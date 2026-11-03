-- forward
CREATE TABLE movements (shop TEXT NOT NULL, sku TEXT NOT NULL, quantity INTEGER NOT NULL, reason TEXT NOT NULL);

-- reverse
DROP TABLE movements;
