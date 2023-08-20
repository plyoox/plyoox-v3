ALTER TABLE leveling_users
    ADD CONSTRAINT leveling_users_unique_key
        UNIQUE (guild_id, user_id);

ALTER TYPE user_permission ADD VALUE 'helper';

alter table public.leveling
    rename column booster_xp_multiplicator to booster_xp_multiplier;

