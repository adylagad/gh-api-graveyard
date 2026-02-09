"""Database models and ORM for historical scan tracking."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


class Scan(Base):
    """Represents a single scan operation."""

    __tablename__ = "scans"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    service_name = Column(String(255), nullable=False, index=True)
    repo = Column(String(512))
    spec_path = Column(String(512))
    logs_path = Column(String(512))
    total_endpoints = Column(Integer, default=0)
    unused_endpoints = Column(Integer, default=0)
    scan_duration_seconds = Column(Float)
    success = Column(Boolean, default=True)
    error_message = Column(Text)

    # Relationships
    endpoints = relationship(
        "EndpointSnapshot", back_populates="scan", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Scan(id={self.id}, service={self.service_name}, timestamp={self.timestamp})>"


class EndpointSnapshot(Base):
    """Represents endpoint state at time of scan."""

    __tablename__ = "endpoint_snapshots"

    id = Column(Integer, primary_key=True)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=False, index=True)
    method = Column(String(10), nullable=False, index=True)
    path = Column(String(512), nullable=False, index=True)
    call_count = Column(Integer, default=0)
    last_seen = Column(DateTime)
    unique_callers = Column(Integer, default=0)
    confidence_score = Column(Float, default=0.0)

    # Relationships
    scan = relationship("Scan", back_populates="endpoints")

    def __repr__(self):
        return (
            f"<EndpointSnapshot(method={self.method}, path={self.path}, calls={self.call_count})>"
        )


class DatabaseManager:
    """Manages database connections and operations."""

    def __init__(self, db_url: str = "sqlite:///gh-api-graveyard.db"):
        """
        Initialize database manager.

        Args:
            db_url: SQLAlchemy database URL (default: SQLite file)
        """
        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_tables(self):
        """Create all database tables."""
        Base.metadata.create_all(self.engine)

    def get_session(self):
        """Get a new database session."""
        return self.SessionLocal()

    def save_scan(
        self,
        service_name: str,
        results: List[dict],
        repo: Optional[str] = None,
        spec_path: Optional[str] = None,
        logs_path: Optional[str] = None,
        duration: Optional[float] = None,
    ) -> Scan:
        """
        Save scan results to database.

        Args:
            service_name: Name of the service
            results: List of endpoint analysis results
            repo: Repository name
            spec_path: Path to OpenAPI spec
            logs_path: Path to logs file
            duration: Scan duration in seconds

        Returns:
            Saved Scan object
        """
        session = self.get_session()
        try:
            # Create scan record
            scan = Scan(
                service_name=service_name,
                repo=repo,
                spec_path=spec_path,
                logs_path=logs_path,
                total_endpoints=len(results),
                unused_endpoints=len([r for r in results if r["call_count"] == 0]),
                scan_duration_seconds=duration,
                success=True,
            )

            # Add endpoint snapshots
            for result in results:
                last_seen = None
                if result.get("last_seen"):
                    try:
                        last_seen = datetime.fromisoformat(
                            result["last_seen"].replace("Z", "+00:00")
                        )
                    except (ValueError, AttributeError):
                        pass

                endpoint = EndpointSnapshot(
                    method=result["method"],
                    path=result["path"],
                    call_count=result.get("call_count", 0),
                    last_seen=last_seen,
                    unique_callers=result.get("unique_callers", 0),
                    confidence_score=result.get("confidence_score", 0.0),
                )
                scan.endpoints.append(endpoint)

            session.add(scan)
            session.commit()
            session.refresh(scan)

            # Eagerly load relationships before closing session
            _ = scan.endpoints  # Force load of endpoints

            return scan

        finally:
            session.close()

    def get_scans(self, service_name: Optional[str] = None, limit: int = 10) -> List[Scan]:
        """
        Get recent scans, optionally filtered by service.

        Args:
            service_name: Filter by service name (optional)
            limit: Maximum number of scans to return

        Returns:
            List of Scan objects
        """
        session = self.get_session()
        try:
            query = session.query(Scan).order_by(Scan.timestamp.desc())

            if service_name:
                query = query.filter(Scan.service_name == service_name)

            scans = query.limit(limit).all()
            
            # Eagerly load relationships before closing session
            for scan in scans:
                _ = scan.endpoints
            
            return scans

        finally:
            session.close()

    def get_scan_by_id(self, scan_id: int) -> Optional[Scan]:
        """Get a specific scan by ID."""
        session = self.get_session()
        try:
            scan = session.query(Scan).filter(Scan.id == scan_id).first()
            if scan:
                # Eagerly load relationships
                _ = scan.endpoints
            return scan
        finally:
            session.close()

    def get_services(self) -> List[str]:
        """Get list of all services that have been scanned."""
        session = self.get_session()
        try:
            services = session.query(Scan.service_name).distinct().order_by(Scan.service_name).all()
            return [s[0] for s in services]
        finally:
            session.close()
