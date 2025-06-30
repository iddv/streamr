from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from .database import get_db

router = APIRouter()

@router.post("/admin/fix-streams-columns")
async def fix_streams_columns():
    """
    Emergency migration endpoint to add missing economic columns to streams table.
    This endpoint will be removed after the migration is complete.
    """
    try:
        db = next(get_db())
        
        # SQL to add missing columns
        migration_sql = """
        ALTER TABLE streams 
        ADD COLUMN IF NOT EXISTS total_gb_delivered DECIMAL(12, 4) DEFAULT 0.00,
        ADD COLUMN IF NOT EXISTS total_cost_usd DECIMAL(10, 4) DEFAULT 0.00,
        ADD COLUMN IF NOT EXISTS platform_fee_usd DECIMAL(10, 4) DEFAULT 0.00,
        ADD COLUMN IF NOT EXISTS creator_payout_usd DECIMAL(10, 4) DEFAULT 0.00;
        """
        
        # Execute the migration
        db.execute(text(migration_sql))
        db.commit()
        
        # Verify columns were added
        verify_sql = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'streams' 
        AND column_name IN ('total_gb_delivered', 'total_cost_usd', 'platform_fee_usd', 'creator_payout_usd')
        ORDER BY column_name;
        """
        
        result = db.execute(text(verify_sql)).fetchall()
        columns_added = [row[0] for row in result]
        
        return {
            "success": True,
            "message": "Successfully added missing economic columns to streams table",
            "columns_added": columns_added
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")
    finally:
        db.close() 