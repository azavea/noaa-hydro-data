package com.azavea.noaa

import cats.implicits._
import com.monovore.decline._
import org.apache.avro.generic.GenericData
import org.apache.avro.SchemaBuilder
//import org.apache.avro.reflect.ReflectData
import org.apache.hadoop.conf.Configuration
import org.apache.hadoop.fs.Path
import org.apache.parquet.avro.AvroParquetWriter
import org.apache.parquet.hadoop.{ParquetFileWriter, ParquetWriter}
import org.apache.parquet.hadoop.metadata.CompressionCodecName
import spire.syntax.cfor._
import ucar.nc2._
import ucar.unidata.io.s3.S3RandomAccessFile

import java.net.URI
import java.sql.Timestamp
import java.time.{Instant, LocalDateTime}
import java.time.format.DateTimeFormatter
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

      // construct schema
      val nc = open(timestampToURI(baseURI, startTime))
      val fid = nc.getVariables.asScala.filter(_.getName == "feature_id")(0)
      val fids = fid.read.copyTo1DJavaArray.asInstanceOf[Array[Int]]
      val nVars = fid.getSize.toInt

      nc.close

      logWarn(s"Loaded $nVars feature IDs")

      logWarn("Constructing schema")

      val schema = fids.foldLeft(
        SchemaBuilder
          .record("NWM")
          .fields()
          .requiredLong("epochSeconds")
      ) { (builder, fid) =>
        builder.requiredInt(s"f${fid}")
      }.endRecord()

      logWarn("Building dataframe")
      // convert each date to a row
      def writeRow(writer: ParquetWriter[GenericData.Record], t: Timestamp) = {
        logWarn(s"Reading data for timestamp $t")
        val nc = open(timestampToURI(baseURI, t))
        val streamflowVar = nc.getVariables.asScala.filter(_.getName == "streamflow").head
        val streamflow = streamflowVar.read.copyTo1DJavaArray.asInstanceOf[Array[Int]]

        val record = new GenericData.Record(schema)
        record.put("epochSeconds", t.toInstant.getEpochSecond)
        cfor(0)(_ < nVars, _ + 1) { i =>
          record.put(s"f${fids(i)}", streamflow(i))
        }
        nc.close

        writer.write(record)
      }

      // write out the parquet
      logWarn("Create ParquetWriter")

      val writer: ParquetWriter[GenericData.Record] = AvroParquetWriter
        .builder(new Path(outputURI.toString))
        .withConf(new Configuration)
        //.withDataModel(ReflectData.get)
        .withCompressionCodec(CompressionCodecName.SNAPPY)
        .withSchema(schema)
        .withWriteMode(ParquetFileWriter.Mode.OVERWRITE)
        .withDictionaryEncoding(false)
        .withValidation(false)
        .build()

      logWarn("Write data to Parquet")
      cfor(startTime)(!_.after(endTime), incrementTimestamp(_, 3600)){ t =>
        writeRow(writer, t)
      }

      writer.close
    }
  }
)

object NetCDFToParquetUtils {

  val logger = org.slf4j.LoggerFactory.getLogger(getClass)

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

  def incrementTimestamp(t: Timestamp, inc: Long): Timestamp =
    Timestamp.from(Instant.ofEpochSecond(t.toInstant.getEpochSecond + inc))

}
