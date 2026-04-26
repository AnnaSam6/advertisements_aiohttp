from aiohttp import web
import jwt
from auth import SECRET_KEY, ALGORITHM


def get_token_from_header(request: web.Request) -> str | None:
    """Извлечение токена из заголовка Authorization"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None
    
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    
    return parts[1]


def decode_token(token: str) -> dict | None:
    """Декодирование токена"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


@web.middleware
async def auth_middleware(request: web.Request, handler):
    """Middleware для проверки авторизации на защищённых маршрутах"""
    
    # Публичные маршруты
    public_routes = ['/register', '/login', '/docs', '/']
    
    if request.path in public_routes or request.path.startswith('/static'):
        return await handler(request)
    
    # Для всех остальных маршрутов проверяем токен
    token = get_token_from_header(request)
    
    if not token:
        return web.json_response({'error': 'Missing or invalid Authorization header'}, status=401)
    
    payload = decode_token(token)
    if not payload:
        return web.json_response({'error': 'Invalid or expired token'}, status=401)
    
    # Добавляем информацию о пользователе в request
    request['user_id'] = payload.get('user_id')
    request['username'] = payload.get('username')
    
    return await handler(request)
