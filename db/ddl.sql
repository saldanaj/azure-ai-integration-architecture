create table patients (
  patient_id varchar(64) primary key,
  mrn varchar(64) unique,
  name nvarchar(200),
  dob date,
  last_encounter_id varchar(64),
  created_utc datetime2 default sysutcdatetime()
);

create table care_tasks (
  task_id varchar(64) primary key,
  patient_id varchar(64) not null references patients(patient_id),
  category varchar(32) check (category in ('lab','med','visit','other')),
  title nvarchar(500) not null,
  due_date date null,
  priority varchar(16) check (priority in ('low','normal','high')),
  source_encounter_id varchar(64),
  status varchar(16) not null default 'open' check (status in ('open','done','cancelled')),
  created_utc datetime2 not null default sysutcdatetime(),
  updated_utc datetime2 not null default sysutcdatetime()
);
create index ix_care_tasks_patient_open on care_tasks(patient_id, status);

create table task_audit (
  audit_id bigint identity primary key,
  task_id varchar(64) not null references care_tasks(task_id),
  action varchar(32) not null,
  actor varchar(128) not null,
  timestamp_utc datetime2 not null default sysutcdatetime(),
  payload_json nvarchar(max)
);

create table processed_events (
  event_id varchar(128) primary key,
  event_type varchar(64) not null,
  patient_id varchar(64) null,
  processed_utc datetime2 not null default sysutcdatetime()
);
