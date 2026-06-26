db = db.getSiblingDB("digital_burnout_v1");

// U10: For low-productivity users, compare burnout risk and mental-state distribution by activity level.
// Default: use productivity_category = "Low" when that category exists.
// If the dataset version does not contain productivity_category = "Low", use:
// { $match: { "burnout_result.productivity_score": { $lte: 56 } } }
const useCategoryLow = true;
const lowProductivityMatch = useCategoryLow
  ? { "burnout_result.productivity_category": "Low" }
  : { "burnout_result.productivity_score": { $lte: 56 } };

const pipeline = [
  {
    $setWindowFields: {
      output: {
        avg_physical_activity: {
          $avg: "$health_wellness.physical_activity",
          window: { documents: ["unbounded", "unbounded"] }
        }
      }
    }
  },
  { $match: lowProductivityMatch },
  {
    $project: {
      activity_level: {
        $cond: [
          { $lt: ["$health_wellness.physical_activity", "$avg_physical_activity"] },
          "below_average",
          "above_average"
        ]
      },
      burnout_risk: "$burnout_result.burnout_risk",
      mental_state: "$burnout_result.mental_state"
    }
  },
  {
    $group: {
      _id: {
        activity_level: "$activity_level",
        mental_state: "$mental_state"
      },
      burnout_risk_sum: { $sum: "$burnout_risk" },
      mental_state_count: { $sum: 1 }
    }
  },
  { $sort: { "_id.activity_level": 1, mental_state_count: -1, "_id.mental_state": 1 } },
  {
    $group: {
      _id: "$_id.activity_level",
      burnout_risk_sum: { $sum: "$burnout_risk_sum" },
      count: { $sum: "$mental_state_count" },
      mental_state_distribution: {
        $push: {
          mental_state: "$_id.mental_state",
          count: "$mental_state_count"
        }
      }
    }
  },
  {
    $project: {
      _id: 0,
      activity_level: "$_id",
      avg_burnout_risk: { $divide: ["$burnout_risk_sum", "$count"] },
      mental_state_distribution: 1,
      count: 1
    }
  },
  { $sort: { activity_level: 1 } }
];

db.v1_wellbeing_assessments.aggregate(pipeline);

// Explain version:
// db.v1_wellbeing_assessments.explain("executionStats").aggregate(pipeline);
