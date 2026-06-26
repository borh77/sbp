db = db.getSiblingDB("digital_burnout_v1");

// U6: Group by focus-session bucket and find averages plus dominant work mode.
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
    $addFields: {
      focus_sessions_bucket: {
        $switch: {
          branches: [
            { case: { $lte: ["$focus_productivity.focus_sessions", 0] }, then: "0" },
            { case: { $lte: ["$focus_productivity.focus_sessions", 3] }, then: "1-3" }
          ],
          default: "4+"
        }
      }
    }
  },
  {
    $group: {
      _id: {
        bucket: "$focus_sessions_bucket",
        work_mode: "$user.work_mode"
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

db.v1_wellbeing_assessments.aggregate(pipeline);

// Explain version:
// db.v1_wellbeing_assessments.explain("executionStats").aggregate(pipeline);
