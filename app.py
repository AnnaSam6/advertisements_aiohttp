from aiohttp import web
import json
import logging
from database import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальный объект БД
db = Database()


def validate_create_data(data: dict) -> tuple:
    """Валидация данных для создания"""
    if not data:
        return False, "No JSON data provided"
    
    required_fields = ['title', 'description', 'owner']
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"
        if not isinstance(data[field], str):
            return False, f"Field '{field}' must be a string"
        if not data[field].strip():
            return False, f"Field '{field}' cannot be empty"
    
    if len(data['title']) > 200:
        return False, "Field 'title' must be less than 200 characters"
    if len(data['owner']) > 100:
        return False, "Field 'owner' must be less than 100 characters"
    
    return True, None


def validate_update_data(data: dict) -> tuple:
    """Валидация данных для обновления"""
    if not data:
        return False, "No JSON data provided"
    
    if 'title' in data:
        if not isinstance(data['title'], str):
            return False, "Field 'title' must be a string"
        if data['title'] and len(data['title']) > 200:
            return False, "Field 'title' must be less than 200 characters"
    
    if 'description' in data:
        if not isinstance(data['description'], str):
            return False, "Field 'description' must be a string"
    
    if 'owner' in data:
        if not isinstance(data['owner'], str):
            return False, "Field 'owner' must be a string"
        if data['owner'] and len(data['owner']) > 100:
            return False, "Field 'owner' must be less than 100 characters"
    
    return True, None


async def handle_create(request: web.Request) -> web.Response:
    """POST /advertisements - создание объявления"""
    try:
        data = await request.json()
        
        is_valid, error = validate_create_data(data)
        if not is_valid:
            return web.json_response({'error': error}, status=400)
        
        advertisement = await db.create_advertisement(
            title=data['title'],
            description=data['description'],
            owner=data['owner']
        )
        
        return web.json_response(advertisement.to_dict(), status=201)
    
    except json.JSONDecodeError:
        return web.json_response({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error creating advertisement: {e}")
        return web.json_response({'error': f'Internal server error: {str(e)}'}, status=500)


async def handle_get(request: web.Request) -> web.Response:
    """GET /advertisements/{id} - получение объявления"""
    try:
        ad_id = int(request.match_info['id'])
        
        advertisement = await db.get_advertisement(ad_id)
        
        if not advertisement:
            return web.json_response(
                {'error': f'Advertisement with id {ad_id} not found'},
                status=404
            )
        
        return web.json_response(advertisement.to_dict(), status=200)
    
    except ValueError:
        return web.json_response({'error': 'Invalid ID format'}, status=400)
    except Exception as e:
        logger.error(f"Error getting advertisement: {e}")
        return web.json_response({'error': f'Internal server error: {str(e)}'}, status=500)


async def handle_update(request: web.Request) -> web.Response:
    """PUT /advertisements/{id} - обновление объявления"""
    try:
        ad_id = int(request.match_info['id'])
        data = await request.json()
        
        is_valid, error = validate_update_data(data)
        if not is_valid:
            return web.json_response({'error': error}, status=400)
        
        advertisement = await db.update_advertisement(ad_id, data)
        
        if not advertisement:
            return web.json_response(
                {'error': f'Advertisement with id {ad_id} not found'},
                status=404
            )
        
        return web.json_response(advertisement.to_dict(), status=200)
    
    except ValueError:
        return web.json_response({'error': 'Invalid ID format'}, status=400)
    except json.JSONDecodeError:
        return web.json_response({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error updating advertisement: {e}")
        return web.json_response({'error': f'Internal server error: {str(e)}'}, status=500)


async def handle_delete(request: web.Request) -> web.Response:
    """DELETE /advertisements/{id} - удаление объявления"""
    try:
        ad_id = int(request.match_info['id'])
        
        deleted = await db.delete_advertisement(ad_id)
        
        if not deleted:
            return web.json_response(
                {'error': f'Advertisement with id {ad_id} not found'},
                status=404
            )
        
        # 204 No Content - пустой ответ
        return web.Response(status=204)
    
    except ValueError:
        return web.json_response({'error': 'Invalid ID format'}, status=400)
    except Exception as e:
        logger.error(f"Error deleting advertisement: {e}")
        return web.json_response({'error': f'Internal server error: {str(e)}'}, status=500)


async def handle_get_all(request: web.Request) -> web.Response:
    """GET /advertisements - получение всех объявлений"""
    try:
        advertisements = await db.get_all_advertisements()
        return web.json_response([ad.to_dict() for ad in advertisements], status=200)
    except Exception as e:
        logger.error(f"Error getting all advertisements: {e}")
        return web.json_response({'error': f'Internal server error: {str(e)}'}, status=500)


async def on_startup(app: web.Application):
    """Запуск при инициализации сервера"""
    await db.init_db()
    logger.info("Server started on http://localhost:8080")


async def on_shutdown(app: web.Application):
    """Завершение при остановке сервера"""
    await db.close()
    logger.info("Server shutdown")


def create_app() -> web.Application:
    """Создание и настройка приложения"""
    app = web.Application()
    
    # Регистрация маршрутов
    app.router.add_post('/advertisements', handle_create)
    app.router.add_get('/advertisements/{id}', handle_get)
    app.router.add_put('/advertisements/{id}', handle_update)
    app.router.add_delete('/advertisements/{id}', handle_delete)
    app.router.add_get('/advertisements', handle_get_all)
    
    # Регистрация обработчиков жизненного цикла
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    return app


if __name__ == '__main__':
    app = create_app()
    web.run_app(app, host='localhost', port=8080)
