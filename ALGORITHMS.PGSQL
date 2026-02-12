INPUT identifier, password

Search database for user where
    username = identifier
    OR email = identifier

IF user exists THEN
    IF entered password matches stored password hash THEN
        Log user in
        Redirect to dashboard
    ELSE
        Display error message
    ENDIF
ELSE
    Display error message
ENDIF



INPUT rating, review_text, game_id

IF rating is between 1 and 5 THEN
    IF user is authenticated THEN
        Create new review record
        Save to database
        Redirect to game page
    ELSE
        Redirect to login page
    ENDIF
ELSE
    Display validation error
ENDIF



INPUT review_id, user_id, reaction_value

Search for existing reaction by user on review

IF reaction exists THEN
    IF existing reaction equals reaction_value THEN
        Remove reaction
    ELSE
        Update reaction value
    ENDIF
ELSE
    Create new reaction
ENDIF