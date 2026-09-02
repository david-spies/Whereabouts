# migrations/script.py.mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
import geoalchemy2  # Added to seamlessly manage PostGIS spatial geometries
${imports}

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    # Ensure PostGIS extension is created before adding geographic tables
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
