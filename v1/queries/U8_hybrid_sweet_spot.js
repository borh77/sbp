db = db.getSiblingDB("digital_burnout_v1");

// U8: For good workspace quality, group productivity and motivation by remote work days.
const pipeline = [
  { $match: { "work_environment.workspace_quality": { $gt: 6 } } },
  {
    $group: {
      _id: "$work_environment.remote_work_days",
      avg_productivity_score: { $avg: "$burnout_result.productivity_score" },
      avg_motivation_level: { $avg: "$burnout_result.motivation_level" },
      count: { $sum: 1 }
    }
  },
  {
    $project: {
      _id: 0,
      remote_work_days: "$_id",
      avg_productivity_score: 1,
      avg_motivation_level: 1,
      count: 1
    }
  },
  { $sort: { remote_work_days: 1 } }
];

db.v1_wellbeing_assessments.aggregate(pipeline);

// Explain version:
// db.v1_wellbeing_assessments.explain("executionStats").aggregate(pipeline);
