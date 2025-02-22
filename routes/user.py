from datetime import timedelta
import sys
import bcrypt
from fastapi import APIRouter
from models.user import tableUser
from models.owner import tableOwner
from models.shop import tableShop
from models.menu import tableMenu
from schemas.user import Usuario, UsuarioUpdate
from config.db import session
from fastapi import Depends, HTTPException, status
from fastapi.responses import RedirectResponse,JSONResponse
from fastapi.security import OAuth2PasswordRequestForm,OAuth2PasswordBearer
from fastapi_login import LoginManager
from fastapi.encoders import jsonable_encoder
from bcrypt import hashpw, gensalt
from sqlalchemy import select
sys.setrecursionlimit(1000)

secret = 'secret_word'
manager = LoginManager(secret,use_cookie=True,token_url='/login')
manager.cookie_name = "access_token"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
userRoute = APIRouter()

@userRoute.get("/")
async def getUsers():
    try:
    # join table user with table owner
    #query = conn.execute(select(tableUser.c.id,tableUser.c.name,tableUser.c.lastname,tableUser.c.url_avatar,tableUser.c.email,tableUser.c.phone,tableUser.c.isowner,tableOwner).select_from(tableUser.join(tableOwner, tableUser.c.id == tableOwner.c.user_id))).fetchall()
        user = session.execute(tableUser.select()).all()
        # return {"Owner":query}
        return user
    except Exception as e:
        return {"Error":str(e)}
        
@userRoute.delete("/auth/delete/{id}")
async def deleteUser(id: int):
    try:
        type = session.execute(tableUser.select().where(tableUser.c.id == id)).first()
        if type == None:
            return {"Error":"No se encontro el usuario"}
        else:
            if type.isowner == 1:
                session.execute(tableOwner.delete().where(tableOwner.c.user_id == id))
                session.execute(tableUser.delete().where(tableUser.c.id == id))
            else:
                session.execute(tableUser.delete().where(tableUser.c.id == id))
            return {"message": "Usuario eliminado exitosamente"}
    except Exception as e:
        return {"Error":str(e)}
        
@userRoute.put("/auth/update/{id}")
async def updateUser(id: int, user: UsuarioUpdate):
    try:
        session.execute(tableUser.update().where(tableUser.c.id == id).values(name=user.name,lastname=user.lastname,url_avatar=user.url_avatar,email=user.email,phone=user.phone))
        return {"message": "Usuario actualizado exitosamente"}
    except Exception as e:
        return {"Error":str(e)}

@userRoute.post('/auth/login')
async def loginUser(data:OAuth2PasswordRequestForm=Depends()):
    try:
        user = load_user(data.username)
        if user == None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
        else: 
            if bcrypt.checkpw(str(data.password).encode('utf-8'),str(user.password).encode('utf-8')):
                access_token = manager.create_access_token(data={"sub":user.email},expires=timedelta(minutes=60))
                response = RedirectResponse(url='/home',status_code=status.HTTP_200_OK)
                response.set_cookie(manager.cookie_name,access_token)
                usuario = {'id':user.id,'name':user.name,'lastname':user.lastname,'email':user.email,'phone':user.phone,'avatar_url':user.url_avatar,"credits":user.credits}
                if user.isowner == 1:
                    isowner = session.execute(select(tableOwner).select_from(tableUser.join(tableOwner, tableOwner.c.user_id == user.id))).first()
                    menus = session.execute(select(tableMenu.c.id,tableShop.c.id).select_from(tableOwner.join(tableShop,tableOwner.c.user_id == tableShop.c.owner_id).join(tableUser,tableOwner.c.user_id == tableUser.c.id).join(tableMenu,tableShop.c.id == tableMenu.c.shop_id)).where(tableOwner.c.user_id == user.id)).fetchall()
                    id_shops= []
                    for menu in menus:
                        id_shops.append({"id_menu":menu[0],"id_shop":menu[1]})                
                    res = {'token':access_token, "Owner":{"user":usuario,"data_owner":[isowner,{"info_shop":id_shops}]}}
                    return JSONResponse(content=jsonable_encoder(res),status_code=status.HTTP_200_OK)
                else:
                    res = {'token':access_token, "Client":[usuario]}
                    return JSONResponse(content=jsonable_encoder(res),status_code=status.HTTP_200_OK)
            else:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'error: {e}')

@userRoute.post('/auth/register')
async def registerUser(data:Usuario):
    try:
        res = session.execute(tableUser.select().where(tableUser.c.email == data.email)).first()
        if res == None:
            if data.isowner == True:
                data.password = hashpw(data.password.encode('utf-8'), gensalt())
                session.execute(tableUser.insert(), data.dict())
                result = session.execute(tableUser.select().where(tableUser.c.email == data.email)).first()
                session.execute(tableOwner.insert(), {'user_id':result.id})
                return JSONResponse(content='Dueño creado correctamente',status_code=status.HTTP_200_OK)
            else:
                data.password = hashpw(data.password.encode('utf-8'), gensalt())
                session.execute(tableUser.insert(), data.dict())
            return JSONResponse(content='Usuario creado correctamente',status_code=status.HTTP_200_OK)
        else:
            return JSONResponse(content='El usuario ya existe',status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return JSONResponse(content=f'{e}',status_code=status.HTTP_400_BAD_REQUEST)

@manager.user_loader()
def load_user(username:str):
    return session.execute(tableUser.select().where(tableUser.c.email == username)).first()
