"""
Production-Grade Persistence Layer
Stores action history, user sessions, and system state
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from infrastructure.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ActionRecord:
    """Record of executed action"""
    timestamp: str
    action: str
    target: str
    status: str  # success, failed, blocked
    user: str
    risk_level: int
    confidence: float
    result: Optional[str] = None
    error: Optional[str] = None


@dataclass
class SessionRecord:
    """User session record"""
    session_id: str
    start_time: str
    end_time: Optional[str] = None
    user: str = "default"
    action_count: int = 0
    notes: Optional[str] = None


class PersistenceLayer:
    """
    SQLite-based persistence for production data
    - Action history
    - Session tracking
    - System state
    - Audit trail
    """

    def __init__(self, db_path: str = "data/assistant.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        
        self._initialize_db()

    def _initialize_db(self):
        """Create database tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Action history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS action_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target TEXT,
                    status TEXT NOT NULL,
                    user TEXT,
                    risk_level INTEGER,
                    confidence REAL,
                    result TEXT,
                    error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Session table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    user TEXT,
                    action_count INTEGER DEFAULT 0,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # System state table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Audit log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    event_data TEXT NOT NULL,
                    user TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indices for performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_action_timestamp 
                ON action_history(timestamp)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_session_user 
                ON sessions(user)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_audit_created_at 
                ON audit_log(created_at)
            ''')
            
            conn.commit()
            logger.info("Database initialized", db_path=str(self.db_path))

    def record_action(self, action: ActionRecord) -> int:
        """Record executed action"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO action_history
                    (timestamp, action, target, status, user, risk_level, 
                     confidence, result, error)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    action.timestamp,
                    action.action,
                    action.target,
                    action.status,
                    action.user,
                    action.risk_level,
                    action.confidence,
                    action.result,
                    action.error
                ))
                conn.commit()
                logger.info(
                    f"Action recorded: {action.action}",
                    action=action.action,
                    status=action.status
                )
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to record action", exception=str(e))
            raise

    def get_action_history(
        self,
        user: Optional[str] = None,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve action history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = "SELECT * FROM action_history WHERE 1=1"
                params = []
                
                if user:
                    query += " AND user = ?"
                    params.append(user)
                
                if status:
                    query += " AND status = ?"
                    params.append(status)
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error("Failed to retrieve action history", exception=str(e))
            return []

    def create_session(
        self,
        session_id: str,
        user: str = "default"
    ) -> bool:
        """Create new session"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO sessions (session_id, start_time, user)
                    VALUES (?, ?, ?)
                ''', (session_id, datetime.utcnow().isoformat(), user))
                conn.commit()
                logger.info(f"Session created", session_id=session_id, user=user)
                return True
        except Exception as e:
            logger.error(f"Failed to create session", exception=str(e))
            return False

    def end_session(self, session_id: str, notes: Optional[str] = None) -> bool:
        """End session"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE sessions 
                    SET end_time = ?, notes = ?
                    WHERE session_id = ?
                ''', (datetime.utcnow().isoformat(), notes, session_id))
                conn.commit()
                logger.info(f"Session ended", session_id=session_id)
                return True
        except Exception as e:
            logger.error(f"Failed to end session", exception=str(e))
            return False

    def increment_session_actions(self, session_id: str) -> bool:
        """Increment action count for session"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE sessions 
                    SET action_count = action_count + 1
                    WHERE session_id = ?
                ''', (session_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error("Failed to increment session actions", exception=str(e))
            return False

    def set_state(self, key: str, value: Any):
        """Store system state"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                value_str = json.dumps(value) if not isinstance(value, str) else value
                
                cursor.execute('''
                    INSERT OR REPLACE INTO system_state (key, value)
                    VALUES (?, ?)
                ''', (key, value_str))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to set state", exception=str(e))

    def get_state(self, key: str) -> Optional[Any]:
        """Retrieve system state"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT value FROM system_state WHERE key = ?",
                    (key,)
                )
                result = cursor.fetchone()
                if result:
                    try:
                        return json.loads(result[0])
                    except json.JSONDecodeError:
                        return result[0]
                return None
        except Exception as e:
            logger.error(f"Failed to get state", exception=str(e))
            return None

    def audit_log(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        user: str = "system"
    ):
        """Log audit event"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO audit_log (event_type, event_data, user)
                    VALUES (?, ?, ?)
                ''', (
                    event_type,
                    json.dumps(event_data),
                    user
                ))
                conn.commit()
        except Exception as e:
            logger.error("Failed to log audit event", exception=str(e))

    def cleanup_old_data(self, days: int = 90) -> int:
        """Remove old records (cleanup)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cutoff_date = (
                    datetime.utcnow() - timedelta(days=days)
                ).isoformat()
                
                cursor.execute(
                    "DELETE FROM action_history WHERE timestamp < ?",
                    (cutoff_date,)
                )
                
                cursor.execute(
                    "DELETE FROM audit_log WHERE created_at < ?",
                    (cutoff_date,)
                )
                
                conn.commit()
                
                deleted = cursor.rowcount
                logger.info(
                    f"Cleaned up old data",
                    records_deleted=deleted,
                    older_than_days=days
                )
                return deleted
        except Exception as e:
            logger.error("Failed to cleanup old data", exception=str(e))
            return 0

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM action_history")
                total_actions = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM sessions")
                total_sessions = cursor.fetchone()[0]
                
                cursor.execute(
                    "SELECT COUNT(*) FROM action_history WHERE status = 'success'"
                )
                successful_actions = cursor.fetchone()[0]
                
                cursor.execute(
                    "SELECT COUNT(*) FROM action_history WHERE status = 'blocked'"
                )
                blocked_actions = cursor.fetchone()[0]
                
                return {
                    "total_actions": total_actions,
                    "total_sessions": total_sessions,
                    "successful_actions": successful_actions,
                    "blocked_actions": blocked_actions,
                    "db_path": str(self.db_path),
                    "db_size_mb": self.db_path.stat().st_size / (1024 * 1024)
                }
        except Exception as e:
            logger.error("Failed to get statistics", exception=str(e))
            return {}


# Global persistence instance
_persistence: Optional[PersistenceLayer] = None


def init_persistence(db_path: str = "data/assistant.db") -> PersistenceLayer:
    """Initialize global persistence layer"""
    global _persistence
    _persistence = PersistenceLayer(db_path)
    return _persistence


def get_persistence() -> PersistenceLayer:
    """Get global persistence instance"""
    global _persistence
    if _persistence is None:
        _persistence = PersistenceLayer()
    return _persistence
