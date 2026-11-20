"""Kafka -> Spark Structured Streaming -> bounded Cassandra time series."""

import os
from pyspark.sql import SparkSession, functions as F, types as T

spark = (SparkSession.builder.appName("mobility-stream")
         .config("spark.sql.session.timeZone", "America/New_York")
         .getOrCreate())
spark.sparkContext.setLogLevel("WARN")
checkpoint_root = os.getenv("CHECKPOINT_ROOT", "/app/checkpoints")

schema = T.StructType([
    T.StructField("trip_id", T.StringType()),
    T.StructField("route_id", T.StringType()),
    T.StructField("origin_zone", T.IntegerType()),
    T.StructField("destination_zone", T.IntegerType()),
    T.StructField("event_time", T.StringType()),
    T.StructField("duration_s", T.IntegerType()),
    T.StructField("distance_km", T.DoubleType()),
    T.StructField("speed_kmh", T.DoubleType()),
])

source = (spark.readStream.format("kafka")
          .option("kafka.bootstrap.servers", os.getenv("KAFKA_BOOTSTRAP", "kafka:19092"))
          .option("subscribe", os.getenv("KAFKA_TOPIC", "taxi-trips"))
          .option("startingOffsets", "earliest")
          .load())
events = (source.select(F.from_json(F.col("value").cast("string"), schema).alias("e"))
          .select("e.*")
          .withColumn("event_time", F.to_timestamp("event_time"))
          .filter("trip_id IS NOT NULL AND route_id IS NOT NULL AND event_time IS NOT NULL"))


def write_table(table):
    def write(batch, batch_id):
        (batch.write.format("org.apache.spark.sql.cassandra")
         .mode("append").options(table=table, keyspace="mobility").save())
    return write


raw = (events.withColumn("bucket_start", F.window("event_time", "15 minutes").start)
       .withColumn("shard", F.pmod(F.xxhash64("trip_id"), F.lit(8)).cast("int")))
raw_query = (raw.writeStream.outputMode("append")
             .foreachBatch(write_table("trip_events"))
             .option("checkpointLocation", f"{checkpoint_root}/raw")
             .start())

windowed = (events.withWatermark("event_time", "30 minutes")
            .groupBy("route_id", F.window("event_time", "5 minutes"))
            .agg(F.count("*").alias("trip_count"),
                 F.avg("duration_s").alias("mean_duration_s"),
                 F.avg("speed_kmh").alias("mean_speed_kmh"),
                 F.avg(F.when(F.col("speed_kmh") < 15, 1.0).otherwise(0.0)).alias("slow_share"))
            .select("route_id", F.to_date(F.col("window.start")).alias("event_date"),
                    F.col("window.start").alias("window_start"), "trip_count",
                    "mean_duration_s", "mean_speed_kmh", "slow_share"))
window_query = (windowed.writeStream.outputMode("update")
                .foreachBatch(write_table("route_windows"))
                .option("checkpointLocation", f"{checkpoint_root}/windows")
                .start())

spark.streams.awaitAnyTermination()
