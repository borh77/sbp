db = db.getSiblingDB("digital_burnout_v1");

db.v1_users.createIndex({ user_id: 1 }, { unique: true });
db.v1_users.createIndex({ occupation: 1 });
db.v1_users.createIndex({ work_mode: 1 });
db.v1_users.createIndex({ device_usage_type: 1 });

db.v1_wellbeing_assessments.createIndex({ user_id: 1 });
db.v1_wellbeing_assessments.createIndex({ "focus_productivity.focus_sessions": 1 });
db.v1_wellbeing_assessments.createIndex({ "digital_behavior.doomscrolling_duration": 1 });
db.v1_wellbeing_assessments.createIndex({
  "work_environment.workspace_quality": 1,
  "work_environment.remote_work_days": 1
});
db.v1_wellbeing_assessments.createIndex({ "digital_behavior.late_night_device_usage": 1 });
db.v1_wellbeing_assessments.createIndex({
  "burnout_result.productivity_category": 1,
  "health_wellness.physical_activity": 1
});
