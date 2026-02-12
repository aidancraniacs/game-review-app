--select statements

--get all users

SELECT * FROM user;

--get all games

SELECT * FROM game;

--get all reviews

SELECT * FROM review;

--get all likes

SELECT * FROM review_like;

--get all reviews for specific game

SELECT *
FROM review
WHERE game_id = 1;

--get all reviews written by specific user

SELECT *
FROM review
WHERE user_id = 1;


--join statements

--get reviews with username and game title

SELECT 
    review.id,
    user.username,
    game.title,
    review.rating,
    review.content
FROM review
JOIN user ON review.user_id = user.id
JOIN game ON review.game_id = game.id;

--get number of likes per review

SELECT
    review.id,
    review.content,
    COUNT(review_like.id) AS like_count
FROM review
LEFT JOIN review_like ON review.id = review_like.review_id
GROUP BY review.id;

--get reviews liked by specific user

SELECT
    review.id,
    review.content,
    game.title
FROM review_like
JOIN review ON review_like.review_id = review.id
JOIN game ON review.game_id = game.id
WHERE review_like.user_id = 1;


--update statements

--update user's email

UPDATE user
SET email = 'newemail@example.com'
WHERE id = 1;

--update review rating

UPDATE review
SET rating = 5
WHERE id = 1;

--update game description

UPDATE game
SET description = 'Updated game description'
WHERE id = 1;


--delete statements

--delete like

DELETE FROM review_like
WHERE id = 1;

--delete review

DELETE FROM review
WHERE id = 1;

--delete user

DELETE FROM user
WHERE id = 1;

--delete game

DELETE FROM game
WHERE id = 1;