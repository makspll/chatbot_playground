

CREATE TABLE user_data (
    ID INT PRIMARY KEY,
    Year_Birth INT NOT NULL, 
    Education VARCHAR(255) NOT NULL, -- customer's level of education
    Marital_Status VARCHAR(255) NOT NULL,
    Income INT, -- customer's yearly household income
    NoOfKidsHome INT NOT NULL, -- number of small children in customer's household
    NoOfTeensHome INT NOT NULL, -- number of teenagers in customer's household
    Dt_Customer DATE NOT NULL, -- date of customer's enrollment with the company
    Recency INT NOT NULL, -- number of days since the last purchase
    MntWines INT NOT NULL, -- amount spent on wine in the last 2 years
    MntFruits INT NOT NULL, -- amount spent on fruits in the last 2 years
    MntMeatProducts INT NOT NULL, -- amount spent on meat in the last 2 years
    MntFishProducts INT NOT NULL, -- amount spent on fish in the last 2 years
    MntSweetProducts INT NOT NULL, -- amount spent on sweets in the last 2 years
    MntGoldProds INT NOT NULL, -- amount spent on gold in the last 2 years
    NumDealsPurchases INT NOT NULL, -- number of purchases made with a discount
    NumWebPurchases INT NOT NULL, -- number of purchases made through the company's web site
    NumCatalogPurchases INT NOT NULL, -- number of purchases made using a catalogue
    NumStorePurchases INT NOT NULL, -- number of purchases made directly in stores
    NumWebVisitsMonth INT NOT NULL, -- number of visits to company's web site in the last month
    AcceptedCmp1 BOOLEAN NOT NULL, -- customer accepted the offer in the 1st campaign
    AcceptedCmp2 BOOLEAN NOT NULL, -- customer accepted the offer in the 2nd campaign
    AcceptedCmp3 BOOLEAN NOT NULL, -- customer accepted the offer in the 3rd campaign
    AcceptedCmp4 BOOLEAN NOT NULL, -- customer accepted the offer in the 4th campaign
    AcceptedCmp5 BOOLEAN NOT NULL, -- customer accepted the offer in the 5th campaign
    Response BOOLEAN NOT NULL, -- customer accepted the offer in the last campaign
    Complain BOOLEAN NOT NULL, -- customer complained in the last 2 years
    Z_CostContact SMALLINT NOT NULL, 
    Z_Revenue SMALLINT NOT NULL
);


LOAD DATA INFILE '/docker-entrypoint-initdb.d/data.csv'
INTO TABLE user_data
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
IGNORE 1 LINES;


-- Read the credentials from the provided user files
SET @username := LOAD_FILE('/docker-entrypoint-initdb.d/user-login.txt');
SET @password := LOAD_FILE('/docker-entrypoint-initdb.d/user-pass.txt');
-- Create a read-only user

SET @sql = CONCAT('CREATE USER IF NOT EXISTS ', QUOTE(@username),'@"%" IDENTIFIED WITH mysql_native_password BY ', QUOTE(@password));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = CONCAT('GRANT SELECT ON prompt_db.* TO ', QUOTE(@username),'@"%"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

FLUSH PRIVILEGES;


