-- HospAI Production Supabase PostgreSQL Schema Migration
-- Migration File: backend/sql/schema.sql
-- Description: Creates tables for model versions, scenario runs, human decision logs, and system audit logs.

-- Enable pgcrypto extension for UUID generation if not already enabled
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- 1. MODEL_VERSIONS TABLE
-- Stores metadata, chronological split dates, and evaluation metrics for ML models.
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.model_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,
    data_type VARCHAR(50) NOT NULL DEFAULT 'excel_dataset',
    dataset_filename VARCHAR(255) NOT NULL DEFAULT 'hackathon_hospital_bottleneck_dataset.xlsx',
    total_rows INTEGER NOT NULL,
    clean_rows INTEGER NOT NULL,
    split_info JSONB NOT NULL DEFAULT '{}'::jsonb,
    task_metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_model_versions_active ON public.model_versions(model_name, is_active);
CREATE INDEX IF NOT EXISTS idx_model_versions_created_at ON public.model_versions(created_at DESC);

-- ============================================================================
-- 2. SCENARIO_RUNS TABLE
-- Records what-if scenario simulation requests, parameters, and baseline vs scenario outputs.
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.scenario_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_reference VARCHAR(100) NOT NULL,
    model_version_id UUID REFERENCES public.model_versions(id) ON DELETE SET NULL,
    season VARCHAR(20) NOT NULL DEFAULT 'normal' CHECK (season IN ('normal', 'monsoon', 'flu', 'outbreak')),
    arrival_multiplier NUMERIC(4, 2) NOT NULL DEFAULT 1.0 CHECK (arrival_multiplier BETWEEN 0.25 AND 3.0),
    bed_delta INTEGER NOT NULL DEFAULT 0 CHECK (bed_delta BETWEEN -10 AND 4),
    staff_delta INTEGER NOT NULL DEFAULT 0 CHECK (staff_delta BETWEEN -8 AND 8),
    discharge_extra INTEGER NOT NULL DEFAULT 0 CHECK (discharge_extra BETWEEN 0 AND 3),
    lab_delta INTEGER NOT NULL DEFAULT 0 CHECK (lab_delta BETWEEN -8 AND 8),
    radiology_delta INTEGER NOT NULL DEFAULT 0 CHECK (radiology_delta BETWEEN -3 AND 5),
    baseline_metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    scenario_metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    bottleneck_warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(50) NOT NULL DEFAULT 'COMPLETED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scenario_runs_snapshot ON public.scenario_runs(snapshot_reference);
CREATE INDEX IF NOT EXISTS idx_scenario_runs_season ON public.scenario_runs(season);
CREATE INDEX IF NOT EXISTS idx_scenario_runs_created_at ON public.scenario_runs(created_at DESC);

-- ============================================================================
-- 3. DECISIONS TABLE
-- Stores human operator decision approvals/rejections linked to scenario evaluations.
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action VARCHAR(255) NOT NULL,
    approved BOOLEAN NOT NULL,
    operator VARCHAR(100) NOT NULL DEFAULT 'Demo operator',
    scenario_run_id UUID REFERENCES public.scenario_runs(id) ON DELETE SET NULL,
    scenario_reference VARCHAR(100),
    modeled_score_improvement NUMERIC(6, 2),
    rationale TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_decisions_scenario_run ON public.decisions(scenario_run_id);
CREATE INDEX IF NOT EXISTS idx_decisions_approved ON public.decisions(approved);
CREATE INDEX IF NOT EXISTS idx_decisions_created_at ON public.decisions(created_at DESC);

-- ============================================================================
-- 4. AUDIT_LOGS TABLE
-- Tracks operational audit trails, administrative actions, clock advances, and resets.
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_type VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id UUID,
    actor VARCHAR(100) NOT NULL DEFAULT 'Demo operator',
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    ip_address INET,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON public.audit_logs(action_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_entity ON public.audit_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON public.audit_logs(created_at DESC);

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================
COMMENT ON TABLE public.model_versions IS 'Tracks ML model versions, datasets, and chronological evaluation metrics.';
COMMENT ON TABLE public.scenario_runs IS 'Records what-if scenario simulations, input parameters, and predicted outcomes.';
COMMENT ON TABLE public.decisions IS 'Stores human operator approvals and rejections of scenario proposals.';
COMMENT ON TABLE public.audit_logs IS 'System-wide audit trail for security, governance, and operational events.';
