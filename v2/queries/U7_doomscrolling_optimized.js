db = db.getSiblingDB("digital_burnout_v2");

// U7 optimized: Use computed doomscrolling buckets and device type from user_ref.
// Buckets match MongoDB $bucket boundaries: [0,1), [1,2), [2,3), and 3+.
const pipeline = [
  {
    $group: {
      _id: {
        bucket: "$computed.doomscrolling_bucket",
        device_usage_type: "$user_ref.device_usage_type"
      },
      max_app_switch_frequency: { $max: "$digital_behavior.app_switch_frequency" },
      notification_sum: { $sum: "$digital_behavior.notification_count" },
      device_count: { $sum: 1 }
    }
  },
  { $sort: { "_id.bucket": 1, device_count: -1, "_id.device_usage_type": 1 } },
  {
    $group: {
      _id: "$_id.bucket",
      max_app_switch_frequency: { $max: "$max_app_switch_frequency" },
      notification_sum: { $sum: "$notification_sum" },
      count: { $sum: "$device_count" },
      most_common_device_usage_type: { $first: "$_id.device_usage_type" }
    }
  },
  {
    $project: {
      _id: 0,
      doomscrolling_bucket: "$_id",
      max_app_switch_frequency: 1,
      avg_notification_count: { $divide: ["$notification_sum", "$count"] },
      most_common_device_usage_type: 1,
      count: 1
    }
  },
  { $sort: { doomscrolling_bucket: 1 } }
];

db.v2_wellbeing_assessments.aggregate(pipeline);

// Explain version:
// db.v2_wellbeing_assessments.explain("executionStats").aggregate(pipeline);
