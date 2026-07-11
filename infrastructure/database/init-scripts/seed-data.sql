-- Placeholder baseline record; replace metrics after first validated training run.
INSERT INTO model_registry (model_version, metrics)
VALUES ('baseline-v1', '{"accuracy": 0.0}'::jsonb)
ON CONFLICT DO NOTHING;
