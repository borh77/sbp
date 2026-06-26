db = db.getSiblingDB("digital_burnout_v2");

db.v2_users.createIndex({ user_id: 1 }, { unique: true });

db.v2_wellbeing_assessments.createIndex({
  "computed.focus_sessions_bucket": 1,
  "user_ref.work_mode": 1
});

db.v2_wellbeing_assessments.createIndex({
  "computed.doomscrolling_bucket": 1,
  "user_ref.device_usage_type": 1
});

const oldU8Index = db.v2_wellbeing_assessments.getIndexes().find((index) => {
  return JSON.stringify(index.key) === JSON.stringify({
    "work_environment.remote_work_days": 1,
    "computed.workspace_quality_ok": 1
  });
});

if (oldU8Index) {
  db.v2_wellbeing_assessments.dropIndex(oldU8Index.name);
}

const unnamedCorrectU8Index = db.v2_wellbeing_assessments.getIndexes().find((index) => {
  return index.name !== "idx_v2_u8_workspace_ok_remote_days" &&
    JSON.stringify(index.key) === JSON.stringify({
      "computed.workspace_quality_ok": 1,
      "work_environment.remote_work_days": 1
    });
});

if (unnamedCorrectU8Index) {
  db.v2_wellbeing_assessments.dropIndex(unnamedCorrectU8Index.name);
}

db.v2_wellbeing_assessments.createIndex(
  {
    "computed.workspace_quality_ok": 1,
    "work_environment.remote_work_days": 1
  },
  { name: "idx_v2_u8_workspace_ok_remote_days" }
);

db.v2_wellbeing_assessments.createIndex({
  "computed.late_night_high": 1,
  "user_ref.occupation": 1
});

db.v2_wellbeing_assessments.createIndex({
  "burnout_result.productivity_category": 1,
  "computed.activity_level": 1,
  "burnout_result.mental_state": 1
});

db.v2_wellbeing_assessments.createIndex({ user_id: 1 });
