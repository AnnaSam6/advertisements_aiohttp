from aiohttp import web
import json
import logging
from database import Database
from auth import hash_password, verify_password, create_access_token, get_user_id_from_token
from middleware import auth_middleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = Database()


# ========== ВАЛИДАЦИЯ ==========

def validate_register_data(data: dict) -> tuple:
    """Валидация данных регистрации"""
    if not data:
        return False, "No JSON data provided"
    
    required = ['username', 'email', 'password']
    for field in required:
        if field not in data:
            return False, f"Missing field: {field}"
        if not data[field] or not str(data[field]).strip():
            return False, f"Field '{field}' cannot be empty"
    
    if len(data['username']) < 3:
        return False, "Username must be at least 3 characters"
    if len(data['username']) > 100:
        return False, "Username too long"
    
    if '@' not in data['email']:
        return False, "Invalid email format"
    
    if len(data['password']) < 6:
        return False, "Password must be at least 6 characters"
    
    return True, None


def validate_advertisement_data(data: dict) -> tuple:
    """Валидация данных объявления"""
    if not data:
        return False, "No JSON data provided"
    
    required = ['title', 'description']
    for field in required:
        if field not in data:
            return False, f"Missing field: {field}"
        if not data[field] or not str(data[field]).strip():
            return False, f"Field '{field}' cannot be empty"
    
    if len(data['title']) > 200:
        return False, "Title too long (max 200 chars)"
    
    return True, None


# ========== PUBLIC ROUTES ==========

async def register(request: web.Request) -> web.Response:
    """POST /register - регистрация пользователя"""
    try:
        data = await request.json()
        
        is_valid, error = validate_register_data(data)
        if not is_valid:
            return web.json_response({'error': error}, status=400)
        
        # Проверка существования пользователя
        existing = await db.get_user_by_username(data['username'])
        if existing:
            return web.json_response({'error': 'Username already exists'}, status=409)
        
        existing_email = await db.get_user_by_email(data['email'])
        if existing_email:
            return web.json_response({'error': 'Email already registered'}, status=409)
        
        # Создание пользователя
        password_hash = hash_password(data['password'])
        user = await db.create_user(data['username'], data['email'], password_hash)
        
        # Создание токена
        token = create_access_token(user.id, user.username)
        
        return web.json_response({
            'message': 'User created successfully',
            'user': user.to_dict(),
            'access_token': token,
            'token_type': 'bearer'
        }, status=201)
        
    except json.JSONDecodeError:
        return web.json_response({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Register error: {e}")
        return web.json_response({'error': 'Internal server error'}, status=500)


async def login(request: web.Request) -> web.Response:
    """POST /login - вход пользователя"""
    try:
        data = await request.json()
        
        if not data or 'username' not in data or 'password' not in data:
            return web.json_response({'error': 'Username and password required'}, status=400)
        
        user = await db.get_user_by_username(data['username'])
        
        if not user or not verify_password(data['password'], user.password_hash):
            return web.json_response({'error': 'Invalid username or password'}, status=401)
        
        token = create_access_token(user.id, user.username)
        
        return web.json_response({
            'message': 'Login successful',
            'user': user.to_dict(),
            'access_token': token,
            'token_type': 'bearer'
        }, status=200)
        
    except json.JSONDecodeError:
        return web.json_response({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Login error: {e}")
        return web.json_response({'error': 'Internal server error'}, status=500)


# ========== PROTECTED ROUTES (требуют токен) ==========

async def create_advertisement(request: web.Request) -> web.Response:
    """POST /advertisements - создание объявления (только авторизованные)"""
    try:
        user_id = request.get('user_id')
        if not user_id:
            return web.json_response({'error': 'Unauthorized'}, status=401)
        
        data = await request.json()
        
        is_valid, error = validate_advertisement_data(data)
        if not is_valid:
            return web.json_response({'error': error}, status=400)
        
        advertisement = await db.create_advertisement(
            title=data['title'],
            description=data['description'],
            user_id=user_id
        )
        
        # Дозагружаем пользователя для ответа
        adv_with_user = await db.get_advertisement_with_user(advertisement.id)
        
        return web.json_response(adv_with_user.to_dict(), status=201)
        
    except json.JSONDecodeError:
        return web.json_response({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Create ad error: {e}")
        return web.json_response({'error': 'Internal server error'}, status=500)


async def get_advertisement(request: web.Request) -> web.Response:
    """GET /advertisements/{id} - получение объявления (публичный)"""
    try:
        ad_id = int(request.match_info['id'])
        
        advertisement = await db.get_advertisement_with_user(ad_id)
        
        if not advertisement:
            return web.json_response({'error': f'Advertisement {ad_id} not found'}, status=404)
        
        return web.json_response(advertisement.to_dict(), status=200)
        
    except ValueError:
        return web.json_response({'error': 'Invalid ID'}, status=400)
    except Exception as e:
        logger.error(f"Get ad error: {e}")
        return web.json_response({'error': 'Internal server error'}, status=500)


async def update_advertisement(request: web.Request) -> web.Response:
    """PUT /advertisements/{id} - обновление (только владелец)"""
    try:
        user_id = request.get('user_id')
        if not user_id:
            return web.json_response({'error': 'Unauthorized'}, status=401)
        
        ad_id = int(request.match_info['id'])
        data = await request.json()
        
        advertisement, result = await db.update_advertisement(ad_id, user_id, data)
        
        if result == 'not_found':
            return web.json_response({'error': f'Advertisement {ad_id} not found'}, status=404)
        
        if result == 'forbidden':
            return web.json_response({'error': 'You can only edit your own advertisements'}, status=403)
        
        return web.json_response(advertisement.to_dict(), status=200)
        
    except ValueError:
        return web.json_response({'error': 'Invalid ID'}, status=400)
    except json.JSONDecodeError:
        return web.json_response({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Update ad error: {e}")
        return web.json_response({'error': 'Internal server error'}, status=500)


async def delete_advertisement(request: web.Request) -> web.Response:
    """DELETE /advertisements/{id} - удаление (только владелец)"""
    try:
        user_id = request.get('user_id')
        if not user_id:
            return web.json_response({'error': 'Unauthorized'}, status=401)
        
        ad_id = int(request.match_info['id'])
        
        success, result = await db.delete_advertisement(ad_id, user_id)
        
        if result == 'not_found':
            return web.json_response({'error': f'Advertisement {ad_id} not found'}, status=404)
        
        if result == 'forbidden':
            return web.json_response({'error': 'You can only delete your own advertisements'}, status=403)
        
        return web.Response(status=204)
        
    except ValueError:
        return web.json_response({'error': 'Invalid ID'}, status=400)
    except Exception as e:
        logger.error(f"Delete ad error: {e}")
        return web.json_response({'error': 'Internal server error'}, status=500)


async def get_all_advertisements(request: web.Request) -> web.Response:
    """GET /advertisements - все объявления (публичный)"""
    try:
        advertisements = await db.get_all_advertisements()
        return web.json_response([ad.to_dict() for ad in advertisements], status=200)
    except Exception as e:
        logger.error(f"Get all ads error: {e}")
        return web.json_response({'error': 'Internal server error'}, status=500)


async def get_my_advertisements(request: web.Request) -> web.Response:
    """GET /advertisements/me - мои объявления (только авторизованные)"""
    try:
        user_id = request.get('user_id')
        if not user_id:
            return web.json_response({'error': 'Unauthorized'}, status=401)
        
        advertisements = await db.get_user_advertisements(user_id)
        return web.json_response([ad.to_dict() for ad in advertisements], status=200)
    except Exception as e:
        logger.error(f"Get my ads error: {e}")
        return web.json_response({'error': 'Internal server error'}, status=500)


async def get_me(request: web.Request) -> web.Response:
    """GET /me - получение информации о текущем пользователе"""
    try:
        user_id = request.get('user_id')
        if not user_id:
            return web.json_response({'error': 'Unauthorized'}, status=401)
        
        user = await db.get_user_by_id(user_id)
        if not user:
            return web.json_response({'error': 'User not found'}, status=404)
        
        return web.json_response(user.to_dict(), status=200)
    except Exception as e:
        logger.error(f"Get me error: {e}")
        return web.json_response({'error': 'Internal server error'}, status=500)


# ========== APP SETUP ==========

async def on_startup(app: web.Application):
    await db.init_db()
    logger.info("Server started on http://localhost:8080")

async def on_shutdown(app: web.Application):
    await db.close()
    logger.info("Server shutdown")


def create_app() -> web.Application:
    app = web.Application(middlewares=[auth_middleware])
    
    # Публичные маршруты
    app.router.add_post('/register', register)
    app.router.add_post('/login', login)
    
    # Защищённые маршруты (требуют JWT)
    app.router.add_post('/advertisements', create_advertisement)
    app.router.add_get('/advertisements', get_all_advertisements)
    app.router.add_get('/advertisements/me', get_my_advertisements)
    app.router.add_get('/advertisements/{id}', get_advertisement)
    app.router.add_put('/advertisements/{id}', update_advertisement)
    app.router.add_delete('/advertisements/{id}', delete_advertisement)
    app.router.add_get('/me', get_me)
    
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    return app


if __name__ == '__main__':
    app = create_app()
    web.run_app(app, host='localhost', port=8080)
