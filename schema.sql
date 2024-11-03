CREATE TABLE Users (
    user_id INT PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    password VARCHAR(255),
    role VARCHAR(10) DEFAULT 'Visitor' CHECK (role IN ('Visitor', 'Admin'))
);

CREATE TABLE Dining_Hall (
    hall_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    location VARCHAR(255)
);

CREATE TABLE Request (
    request_id SERIAL PRIMARY KEY,
    user_id INT,
    request_food_item VARCHAR(255),
    description TEXT,
    request_status VARCHAR(10) DEFAULT 'pending' CHECK (request_status IN ('pending', 'denied', 'approved')),
    request_date DATE CHECK (request_date <= CURRENT_DATE),
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

CREATE TABLE Record (
    record_id SERIAL PRIMARY KEY,
    food_id INT,
    user_id INT,
    content TEXT,
    time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (food_id) REFERENCES Food(food_id),
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

CREATE TABLE Food_DiningHall (
    food_id INT,
    hall_id INT,
    PRIMARY KEY (food_id, hall_id),
    FOREIGN KEY (food_id) REFERENCES Food(food_id),
    FOREIGN KEY (hall_id) REFERENCES Dining_Hall(hall_id)
);

CREATE TABLE Food (
    food_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    protein DECIMAL(5, 2) CHECK (protein >= 0),
    carbs DECIMAL(5, 2) CHECK (carbs >= 0),
    fat DECIMAL(5, 2) CHECK (fat >= 0),
    sugar DECIMAL(5, 2) CHECK (sugar >= 0),
    calories INT CHECK (calories >= 0),
    serving_size VARCHAR(100),
    category VARCHAR(20) CHECK (category IN ('Breakfast', 'Lunch', 'Dinner', 'Other'))
);

CREATE TABLE Request (
    request_id SERIAL PRIMARY KEY,
    user_id INT,
    request_food_item VARCHAR(255),
    description TEXT,
    request_status VARCHAR(10) DEFAULT 'pending' CHECK (request_status IN ('pending', 'denied', 'approved')),
    request_date DATE CHECK (request_date <= CURRENT_DATE),
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);