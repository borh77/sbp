db = db.getSiblingDB("digital_burnout_v1");

// U9: For high late-night device usage, group health degradation metrics by occupation.
// In this dataset, late_night_device_usage is a binary indicator:
// 1 = late-night device usage happened
// 0 = no late-night device usage
const lateNightUsageValue = 1;
// If using another dataset version where this field is a 1-10 score,
// replace the match with: { $gt: 6 }.

const pipeline = [
  { $match: { "digital_behavior.late_night_device_usage": lateNightUsageValue } },
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
    $group: {
      _id: "$user.occupation",
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

db.v1_wellbeing_assessments.aggregate(pipeline);

// Explain version:
// db.v1_wellbeing_assessments.explain("executionStats").aggregate(pipeline);
