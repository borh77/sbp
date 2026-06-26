db = db.getSiblingDB("digital_burnout_v2");

// U9 optimized: Use computed late_night_high and occupation from user_ref.
// computed.late_night_high is computed from the binary late_night_device_usage
// indicator when the dataset contains 0/1 values.
const pipeline = [
  { $match: { "computed.late_night_high": true } },
  {
    $group: {
      _id: "$user_ref.occupation",
      avg_stress_level: { $avg: "$health_wellness.stress_level" },
      avg_sleep_quality: { $avg: "$health_wellness.sleep_quality" },
      avg_caffeine_intake: { $avg: "$health_wellness.caffeine_intake" },
      count: { $sum: 1 }
    }
  },
  {
    $project: {
      _id: 0,
      occupation: "$_id",
      avg_stress_level: 1,
      avg_sleep_quality: 1,
      avg_caffeine_intake: 1,
      count: 1
    }
  },
  { $sort: { avg_stress_level: -1 } }
];

db.v2_wellbeing_assessments.aggregate(pipeline);

// Explain version:
// db.v2_wellbeing_assessments.explain("executionStats").aggregate(pipeline);
