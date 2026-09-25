-- REFERENCE ONLY: the application creates missing tables in local development.
-- Do not run this on a database that already contains these tables.

CREATE TABLE users (
	id VARCHAR(36) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	plan VARCHAR(30) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE courses (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	degree VARCHAR(50) NOT NULL, 
	subject VARCHAR(150) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_courses_user_id ON courses (user_id);

CREATE TABLE documents (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	filename VARCHAR(255) NOT NULL, 
	storage_key VARCHAR(500), 
	embedding_status VARCHAR(30) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_documents_user_id ON documents (user_id);

CREATE TABLE document_chunks (
	id VARCHAR(36) NOT NULL, 
	document_id VARCHAR(36) NOT NULL, 
	chunk_no INTEGER NOT NULL, 
	page_number INTEGER, 
	text TEXT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(document_id) REFERENCES documents (id)
);

CREATE INDEX ix_document_chunks_document_id ON document_chunks (document_id);

CREATE TABLE learning_sessions (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	course_id VARCHAR(36) NOT NULL, 
	current_topic VARCHAR(255) NOT NULL, 
	current_provider VARCHAR(30) NOT NULL, 
	summary TEXT, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(course_id) REFERENCES courses (id)
);

CREATE INDEX ix_learning_sessions_course_id ON learning_sessions (course_id);

CREATE INDEX ix_learning_sessions_user_id ON learning_sessions (user_id);

CREATE TABLE learning_state (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	course_id VARCHAR(36) NOT NULL, 
	concept VARCHAR(255) NOT NULL, 
	mastery_score FLOAT NOT NULL, 
	attempt_count INTEGER NOT NULL, 
	correct_count INTEGER NOT NULL, 
	weakness TEXT, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(course_id) REFERENCES courses (id)
);

CREATE INDEX ix_learning_state_course_id ON learning_state (course_id);

CREATE INDEX ix_learning_state_user_id ON learning_state (user_id);

CREATE INDEX ix_learning_state_concept ON learning_state (concept);

CREATE TABLE ai_usage (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	session_id VARCHAR(36) NOT NULL, 
	provider VARCHAR(30) NOT NULL, 
	input_tokens INTEGER NOT NULL, 
	output_tokens INTEGER NOT NULL, 
	estimated_cost FLOAT NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(session_id) REFERENCES learning_sessions (id)
);

CREATE INDEX ix_ai_usage_user_id ON ai_usage (user_id);

CREATE INDEX ix_ai_usage_session_id ON ai_usage (session_id);

CREATE TABLE messages (
	id VARCHAR(36) NOT NULL, 
	session_id VARCHAR(36) NOT NULL, 
	`role` VARCHAR(20) NOT NULL, 
	content TEXT NOT NULL, 
	provider VARCHAR(30), 
	input_tokens INTEGER NOT NULL, 
	output_tokens INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(session_id) REFERENCES learning_sessions (id)
);

CREATE INDEX ix_messages_created_at ON messages (created_at);

CREATE INDEX ix_messages_session_id ON messages (session_id);

CREATE TABLE mistakes (
	id VARCHAR(36) NOT NULL, 
	session_id VARCHAR(36) NOT NULL, 
	concept VARCHAR(255) NOT NULL, 
	mistake_type VARCHAR(120) NOT NULL, 
	explanation TEXT, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(session_id) REFERENCES learning_sessions (id)
);

CREATE INDEX ix_mistakes_session_id ON mistakes (session_id);

CREATE TABLE practice_attempts (
	id VARCHAR(36) NOT NULL, 
	session_id VARCHAR(36) NOT NULL, 
	concept VARCHAR(255) NOT NULL, 
	mode VARCHAR(30) NOT NULL, 
	question_id VARCHAR(100) NOT NULL, 
	answer TEXT NOT NULL, 
	feedback_json TEXT NOT NULL, 
	created_at DATETIME(6) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(session_id) REFERENCES learning_sessions (id)
);

CREATE INDEX ix_practice_attempts_session_id ON practice_attempts (session_id);

CREATE TABLE session_documents (
	session_id VARCHAR(36) NOT NULL, 
	document_id VARCHAR(36) NOT NULL, 
	PRIMARY KEY (session_id, document_id), 
	FOREIGN KEY(session_id) REFERENCES learning_sessions (id), 
	FOREIGN KEY(document_id) REFERENCES documents (id)
);

CREATE TABLE session_memory (
	session_id VARCHAR(36) NOT NULL, 
	state_json TEXT NOT NULL, 
	next_turn INTEGER NOT NULL, 
	summary_through_turn INTEGER NOT NULL, 
	PRIMARY KEY (session_id), 
	FOREIGN KEY(session_id) REFERENCES learning_sessions (id)
);

CREATE TABLE video_segments (
	id VARCHAR(36) NOT NULL, 
	session_id VARCHAR(36) NOT NULL, 
	video_id VARCHAR(11) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	topic VARCHAR(255) NOT NULL, 
	start_seconds INTEGER NOT NULL, 
	end_seconds INTEGER NOT NULL, 
	evidence TEXT NOT NULL, 
	verification VARCHAR(40) NOT NULL, 
	created_at DATETIME(6) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(session_id) REFERENCES learning_sessions (id)
);

CREATE INDEX ix_video_segments_session_id ON video_segments (session_id);

CREATE TABLE chat_turns (
	id VARCHAR(36) NOT NULL, 
	request_id VARCHAR(36) NOT NULL, 
	request_hash VARCHAR(64) NOT NULL, 
	session_id VARCHAR(36) NOT NULL, 
	turn_no INTEGER NOT NULL, 
	user_message_id VARCHAR(36) NOT NULL, 
	assistant_message_id VARCHAR(36) NOT NULL, 
	response_json TEXT NOT NULL, 
	created_at DATETIME(6) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_session_turn UNIQUE (session_id, turn_no), 
	UNIQUE (request_id), 
	FOREIGN KEY(session_id) REFERENCES learning_sessions (id), 
	FOREIGN KEY(user_message_id) REFERENCES messages (id), 
	FOREIGN KEY(assistant_message_id) REFERENCES messages (id)
);

CREATE INDEX ix_chat_turns_session_id ON chat_turns (session_id);

CREATE TABLE provider_calls (
	id VARCHAR(36) NOT NULL, 
	session_id VARCHAR(36) NOT NULL, 
	turn_id VARCHAR(36) NOT NULL, 
	provider VARCHAR(30) NOT NULL, 
	model VARCHAR(120) NOT NULL, 
	input_tokens INTEGER NOT NULL, 
	output_tokens INTEGER NOT NULL, 
	estimated_cost FLOAT, 
	route_events_json TEXT NOT NULL, 
	created_at DATETIME(6) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(session_id) REFERENCES learning_sessions (id), 
	FOREIGN KEY(turn_id) REFERENCES chat_turns (id)
);

CREATE INDEX ix_provider_calls_session_id ON provider_calls (session_id);
