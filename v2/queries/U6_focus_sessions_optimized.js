db = db.getSiblingDB("digital_burnout_v2");

// U6 optimized: Group by computed focus bucket and find dominant work mode from user_ref.
const pipeline = [
  {
    $group: {
      _id: {
        bucket: "$computed.focus_sessions_bucket",
        work_mode: "$user_ref.work_mode"
      },
      deep_work_sum: { $sum: "$focus_productivity.deep_work_hours" },
      task_completion_sum: { $sum: "$focus_productivity.task_completion_rate" },
      mode_count: { $sum: 1 }
    }
  },
  { $sort: { "_id.bucket": 1, mode_count: -1, "_id.work_mode": 1 } },
  {
    $group: {
      _id: "$_id.bucket",
      deep_work_sum: { $sum: "$deep_work_sum" },
      task_completion_sum: { $sum: "$task_completion_sum" },
      count: { $sum: "$mode_count" },
      dominant_work_mode: { $first: "$_id.work_mode" }
    }
  },
  {
    $project: {
      _id: 0,
      focus_sessions_bucket: "$_id",
      avg_deep_work_hours: { $divide: ["$deep_work_sum", "$count"] },
      avg_task_completion_rate: { $divide: ["$task_completion_sum", "$count"] },
      dominant_work_mode: 1,
      count: 1
    }
  },
  { $sort: { focus_sessions_bucket: 1 } }
];

db.v2_wellbeing_assessments.aggregate(pipeline);

// Explain version:
// db.v2_wellbeing_assessments.explain("executionStats").aggregate(pipeline);
