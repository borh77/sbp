db = db.getSiblingDB("digital_burnout_v1");

// U7: Bucket doomscrolling duration and find attention disruption metrics plus most common device type.
// Buckets use MongoDB $bucket boundaries: [0,1), [1,2), [2,3), and 3+.
const pipeline = [
  {
    $lookup: {
      from: "v1_users",
      localField: "user_id",
      foreignField: "user_id",
      as: "user"
    }
  },
  { $unwind: "$user" },
  {
    $bucket: {
      groupBy: "$digital_behavior.doomscrolling_duration",
      boundaries: [0, 1, 2, 3, 1000000000],
      default: "other",
      output: {
        max_app_switch_frequency: { $max: "$digital_behavior.app_switch_frequency" },
        notification_sum: { $sum: "$digital_behavior.notification_count" },
        count: { $sum: 1 },
        device_usage_types: { $push: "$user.device_usage_type" }
      }
    }
  },
  { $match: { _id: { $ne: "other" } } },
  { $unwind: "$device_usage_types" },
  {
    $group: {
      _id: {
        bucket: "$_id",
        device_usage_type: "$device_usage_types"
      },
      device_count: { $sum: 1 },
      max_app_switch_frequency: { $first: "$max_app_switch_frequency" },
      notification_sum: { $first: "$notification_sum" },
      count: { $first: "$count" }
    }
  },
  { $sort: { "_id.bucket": 1, device_count: -1, "_id.device_usage_type": 1 } },
  {
    $group: {
      _id: "$_id.bucket",
      max_app_switch_frequency: { $first: "$max_app_switch_frequency" },
      notification_sum: { $first: "$notification_sum" },
      count: { $first: "$count" },
      most_common_device_usage_type: { $first: "$_id.device_usage_type" }
    }
  },
  {
    $project: {
      _id: 0,
      doomscrolling_bucket: {
        $switch: {
          branches: [
            { case: { $eq: ["$_id", 0] }, then: "0-1" },
            { case: { $eq: ["$_id", 1] }, then: "1-2" },
            { case: { $eq: ["$_id", 2] }, then: "2-3" },
            { case: { $eq: ["$_id", 3] }, then: "3+" }
          ],
          default: "other"
        }
      },
      max_app_switch_frequency: 1,
      avg_notification_count: { $divide: ["$notification_sum", "$count"] },
      most_common_device_usage_type: 1,
      count: 1
    }
  },
  { $sort: { doomscrolling_bucket: 1 } }
];

db.v1_wellbeing_assessments.aggregate(pipeline);

// Explain version:
// db.v1_wellbeing_assessments.explain("executionStats").aggregate(pipeline);
