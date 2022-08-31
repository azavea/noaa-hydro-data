package com.azavea.noaa

import cats.implicits._
import com.monovore.decline._
import org.apache.spark.SparkConf
import org.apache.spark.serializer.{KryoRegistrator, KryoSerializer}
import org.apache.spark.sql.{Row, SparkSession}
import org.apache.spark.sql.catalyst.encoders.RowEncoder
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._
import spire.syntax.cfor._
import ucar.nc2._
import ucar.unidata.io.s3.S3RandomAccessFile

import java.net.URI
import java.sql.Timestamp
import java.time.{LocalDateTime, YearMonth}
import java.time.format.DateTimeFormatter
import scala.annotation.tailrec
import scala.collection.JavaConverters._

object Main extends CommandApp (
  name = "noaa-netcdf-to-parquet",
  header = "Convert a NWM netCDF file to a wide parquet",
  main = {
    (
      Opts.option[String](
        "start-date",
        short="s",
        help="Datetime to begin processing, in form of yyyyMMddHH [default 1979020101]"
      ).withDefault("1979020101"),
      Opts.option[String](
        "end-date",
        short="e",
        help="Datetime to end processing, in form of yyyyMMddHH [default 2020123123]"
      ).withDefault("2020123123"),
      Opts.option[URI](
        "base-uri",
        help="S3 URI holding NetCDF archive [default=s3://noaa-nwm-retrospective-2-1-pds/model_output/]"
      ).withDefault(new URI("s3://noaa-nwm-retrospective-2-1-pds/model_output/")),
      Opts.option[URI](
        "output",
        short="o",
        help="URI to write Parquet output to"
      )
    ).mapN { (startStr, endStr, baseURI, outputURI) =>
      import NetCDFToParquetUtils._

      val minTime = parseTime("1979020101")
      val maxTime = parseTime("2020123123")

      val startTime = ({ t: Timestamp =>
        if (t.before(minTime))
          minTime
        else
          t
      })(parseTime(startStr))

      val endTime = ({ t: Timestamp =>
        if (t.after(maxTime))
          maxTime
        else
          t
      })(parseTime(endStr))

      val appName = "NWM NetCDF to Parquet"

      val conf = new SparkConf()
        .setIfMissing("spark.master", "local[*]")
        .setAppName(s"${appName}")
        .set("spark.sql.orc.impl", "native")
        .set("spark.sql.orc.filterPushdown", "true")
        .set("spark.sql.parquet.mergeSchema", "false")
        .set("spark.sql.parquet.filterPushdown", "true")
        .set("spark.sql.hive.metastorePartitionPruning", "true")
        .set("spark.ui.showConsoleProgress", "true")
        .set("spark.serializer", classOf[KryoSerializer].getName)
        .set("spark.kryo.registrator", classOf[KryoRegistrator].getName)

      val spark = SparkSession.builder
        .config(conf)
        .enableHiveSupport
        .getOrCreate

      import spark.implicits._

      // create a dataset with the dates
      val daysInMonthUDF = udf { (y: Int, m: Int) =>
        Seq.range(1, YearMonth.of(y, m).lengthOfMonth + 1).toArray
      }

      val timestampOf = udf { (year: Int, month: Int, day: Int, hour: Int) =>
        Timestamp.valueOf(LocalDateTime.of(year, month, day, hour, 0))
      }

      val inRange = udf {
        ts: Timestamp => !(ts.before(startTime) || ts.after(endTime))
      }

      val allTimes = spark
        .createDataset(Seq.range(startTime.getYear + 1900, endTime.getYear + 1901))
        .withColumnRenamed("value", "year")
        .withColumn("month", explode(lit(Seq.range(1,13).toArray)))
        .withColumn("day", explode(daysInMonthUDF('year, 'month)))
        .withColumn("hour", explode(lit(Seq.range(0,24).toArray)))
        .withColumn("timestamp", timestampOf('year, 'month, 'day, 'hour))
        .drop("year", "month", "day", "hour")
        .filter(inRange('timestamp))
        .as[Timestamp]

      // construct schema
      val nc = open(timestampToURI(baseURI, startTime))
      val fid = nc.getVariables.asScala.filter(_.getName == "feature_id")(0)
      val fids = fid.read.copyTo1DJavaArray.asInstanceOf[Array[Int]]
      val nVars = fid.getSize.toInt

      //val latitude = nc.getVariables.filter(_.getName == "latitude")(0)
      //val lat = latitude.read.get1DJavaArray(latitude.getDataType).asInstanceOf[Array[Float]]
      //val longitude = nc.getVariables.filter(_.getName == "longitude")(0)
      //val long = longitude.read.get1DJavaArray(longitude.getDataType).asInstanceOf[Array[Float]]

      nc.close

      logWarn(s"Loaded $nVars feature IDs")

      logWarn("Constructing schema")
      // val schema = StructType(Range(-1, nVars).map{ i =>
      //   //val mdb = new MetadataBuilder
      //   //mdb.putDouble("lat", lat(i).toDouble)
      //   //mdb.putDouble("long", long(i).toDouble)
      //   if (i == -1)
      //     StructField(
      //       "timestamp",
      //       TimestampType,
      //       false
      //     )
      //   else
      //     StructField(
      //       fids(i).toString,
      //       IntegerType,
      //       true
      //       //mdb.build
      //     )
      // })
      val schema = StructType(
        StructField("timestamp", TimestampType, false) +: generateFields(fids, 0)
      )
      logWarn("Constructing encoder")
      val encoder = RowEncoder(schema)

      logWarn("Building dataframe")
      // convert each date to a row
      def timestampToRow(t: Timestamp): Row = {
        logWarn(s"Reading data for timestamp $t")
        val nc = open(timestampToURI(baseURI, t))
        val streamflowVar = nc.getVariables.asScala.filter(_.getName == "streamflow").head
        val streamflow = streamflowVar.read.copyTo1DJavaArray.asInstanceOf[Array[Int]]
        val rowdata = Array.ofDim[Any](nVars + 1)
        rowdata(0) = t
        cfor(0)(_ < nVars, _ + 1) { i =>
          rowdata(i+1) = streamflow(i)
        }
        nc.close
        Row(rowdata: _*)
      }
      val df = allTimes.map(timestampToRow(_))(encoder).toDF

      // write out the parquet
      logWarn("Writing Parquet")
      df.write.parquet(outputURI.toString)

      spark.stop
    }
  }
)

object NetCDFToParquetUtils {

  val logger = org.apache.log4j.Logger.getLogger(getClass())

  def logDebug(msg: => String) = logger.debug(msg)
  def logWarn(msg: => String) = logger.warn(msg)
  def logError(msg: => String) = logger.error(msg)

  def open(uri: URI) = {
    if (uri.getScheme == "s3") {
      val raf = new S3RandomAccessFile(uri.toString, 1<<15, 1<<24)
      NetcdfFile.open(raf, uri.toString, null, null)
    } else {
      NetcdfFile.open(uri.toString)
    }
  }

  val dtFormatter = DateTimeFormatter.ofPattern("yyyyMMddHH")

  def parseTime(timeStr: String): Timestamp =
    Timestamp.valueOf(LocalDateTime.parse(timeStr, dtFormatter))

  def timestampToURI(baseURI: URI, t: Timestamp): URI = {
    val year = t.getYear + 1900
    val timeCode = t.toLocalDateTime.format(dtFormatter) ++ "00"

    baseURI.resolve(s"$year/$timeCode.CHRTOUT_DOMAIN1.comp")
  }

  def generateFields(ids: Array[Int], i: Int): List[StructField] = {
    var l: List[StructField] = Nil
    cfor(0)(_ < ids.size, _ + 1) { i =>
      l = StructField(
        ids(i).toString,
        IntegerType,
        false
      ) +: l
    }
    l
  }



}
