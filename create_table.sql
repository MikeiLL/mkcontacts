-- Table names are flush left, and column definitions are
-- indented by at least one space or tab. Blank lines and
-- lines beginning with a double hyphen are comments.

contacts
    id serial primary key
    fullname varchar
    email varchar unique
    phone varchar unique
    CONSTRAINT at_least_one_contact_point CHECK ((NULLIF(email , '')) IS NOT NULL OR (NULLIF(phone, '') IS NOT NULL))
--    address references city

users
    id serial primary key
    email varchar not null unique
    displayname varchar not null
    user_level int not null default 1 -- noaccess=0, manager=1, admin=3
    password varchar not null default ''

--city
--    id serial primary key
--    name varchar not null
--
--state
--    id serial primary key
