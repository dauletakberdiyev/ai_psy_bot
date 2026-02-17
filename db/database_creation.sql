CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    telegram_user_id BIGINT UNIQUE NOT NULL,
    telegram_chat_id BIGINT UNIQUE,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    language_code TEXT DEFAULT 'ru',
    timezone TEXT,
    is_blocked BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_users_telegram_user_id ON users (telegram_user_id);

CREATE TABLE user_settings (
    user_id UUID PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
    preferred_style TEXT NOT NULL DEFAULT 'cbt',
    -- варианты: cbt, supportive, short, more_questions
    response_length TEXT NOT NULL DEFAULT 'medium',
    -- short | medium | long
    allow_memory BOOLEAN NOT NULL DEFAULT TRUE,
    allow_sensitive_topics BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'active',
    -- active | archived
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at TIMESTAMPTZ,
    last_message_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_sessions_user_id ON sessions (user_id);

CREATE INDEX idx_sessions_last_message_at ON sessions (last_message_at);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    session_id UUID NOT NULL REFERENCES sessions (id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    -- user | assistant | system | developer
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    meta JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_messages_session_id_created_at ON messages (session_id, created_at);

CREATE INDEX idx_messages_user_id_created_at ON messages (user_id, created_at);

CREATE TABLE risk_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    session_id UUID REFERENCES sessions (id) ON DELETE SET NULL,
    message_id UUID REFERENCES messages (id) ON DELETE SET NULL,
    risk TEXT NOT NULL,
    -- none | low | medium | high
    category TEXT NOT NULL,
    -- none | self_harm | harm_others | violence | psychosis
    reasons TEXT [] NOT NULL DEFAULT ARRAY[]::TEXT [],
    raw_detector_output JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_risk_events_user_id_created_at ON risk_events (user_id, created_at);

CREATE INDEX idx_risk_events_risk ON risk_events (risk);

CREATE INDEX idx_risk_events_category ON risk_events (category);

CREATE TABLE memory_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    session_id UUID REFERENCES sessions (id) ON DELETE SET NULL,
    summary TEXT NOT NULL,
    main_topics TEXT [] NOT NULL DEFAULT ARRAY[]::TEXT [],
    user_emotions TEXT [] NOT NULL DEFAULT ARRAY[]::TEXT [],
    key_thoughts TEXT [] NOT NULL DEFAULT ARRAY[]::TEXT [],
    triggers TEXT [] NOT NULL DEFAULT ARRAY[]::TEXT [],
    helpful_strategies_used TEXT [] NOT NULL DEFAULT ARRAY[]::TEXT [],
    next_session_goal TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_memory_summaries_user_id_created_at ON memory_summaries (user_id, created_at);

CREATE TABLE memory_facts (
    user_id UUID PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
    profile JSONB NOT NULL DEFAULT '{}'::jsonb,
    stable_issues TEXT [] NOT NULL DEFAULT ARRAY[]::TEXT [],
    values_and_goals TEXT [] NOT NULL DEFAULT ARRAY[]::TEXT [],
    common_triggers TEXT [] NOT NULL DEFAULT ARRAY[]::TEXT [],
    cognitive_patterns TEXT [] NOT NULL DEFAULT ARRAY[]::TEXT [],
    preferred_support_style TEXT [] NOT NULL DEFAULT ARRAY[]::TEXT [],
    hard_limits TEXT [] NOT NULL DEFAULT ARRAY[]::TEXT [],
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_memory_facts_profile_gin ON memory_facts USING GIN (profile);

CREATE TABLE usage_limits (
    user_id UUID PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
    daily_message_limit INT NOT NULL DEFAULT 20,
    daily_message_used INT NOT NULL DEFAULT 0,
    daily_reset_at DATE NOT NULL DEFAULT CURRENT_DATE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    -- telegram | stripe | manual | kaspi
    status TEXT NOT NULL DEFAULT 'inactive',
    -- inactive | active | canceled | expired
    plan TEXT NOT NULL DEFAULT 'basic',
    -- basic | pro
    started_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    provider_meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_subscriptions_user_id ON subscriptions (user_id);

CREATE INDEX idx_subscriptions_status ON subscriptions (status);

CREATE INDEX idx_subscriptions_expires_at ON subscriptions (expires_at);

CREATE TABLE llm_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    user_id UUID REFERENCES users (id) ON DELETE SET NULL,
    session_id UUID REFERENCES sessions (id) ON DELETE SET NULL,
    message_id UUID REFERENCES messages (id) ON DELETE SET NULL,
    provider TEXT NOT NULL,
    -- openai | deepseek | anthropic | local
    model TEXT NOT NULL,
    prompt_tokens INT,
    completion_tokens INT,
    total_tokens INT,
    latency_ms INT,
    cost_usd NUMERIC(10, 6),
    status TEXT NOT NULL DEFAULT 'success',
    -- success | error
    error_code TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_llm_requests_user_id_created_at ON llm_requests (user_id, created_at);

CREATE INDEX idx_llm_requests_status ON llm_requests (status);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_subscriptions_updated_at
BEFORE UPDATE ON subscriptions
FOR EACH ROW EXECUTE FUNCTION set_updated_at();