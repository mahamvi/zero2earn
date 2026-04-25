from zero2earn_backend.db import init_db, seed_demo

if __name__ == '__main__':
    init_db()
    seed_demo()
    print('Seed complete.')
