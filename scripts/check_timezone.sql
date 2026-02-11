SELECT column_name, column_default, is_nullable 
FROM information_schema.columns 
WHERE table_name='agents' AND column_name='timezone';
