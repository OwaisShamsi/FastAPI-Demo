import asyncio
from fastapi import FastAPI, HTTPException, Depends, WebSocket
from sqlalchemy import create_engine, Column, Integer, String, select
from sqlalchemy.sql import text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from fastapi.middleware.cors import CORSMiddleware
from pymysqlreplication import BinLogStreamReader
from pymysqlreplication.row_event import DeleteRowsEvent, UpdateRowsEvent, WriteRowsEvent
import threading
from fastapi_socketio import SocketManager



# Database settings
# DATABASE_URL = "mssql+pyodbc://sa:root123@LP120\\SQLEXPRESS/test?driver=ODBC+Driver+17+for+SQL+Server"
DATABASE_URL = "mysql+mysqlconnector://root:root123@localhost:3306/test"

#FOR BingLogReader
MYSQL_SETTINGS = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "passwd": "root123"
}

# SQLAlchemy models
Base = declarative_base()

class User(Base):
    __tablename__ = "User"
    id = Column(Integer, primary_key=True, index=True)
    Name = Column(String, index=True)
    phoneNumber = Column(String)

# Database engine and session creation
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# FastAPI settings
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200/"],  # Adjust as needed for your security requirements
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
socket_manager = SocketManager(app=app)

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@socket_manager.on('join')
async def handle_join(sid, *args, **kwargs):
    print(f"user connected with sid : {sid}")
    await app.sio.emit('lobby', 'User joined')

@socket_manager.on("startup")
async def InitialDataInvoke(sid):
    db = SessionLocal()
    users = db.execute(select(User)).all()
    userdata = [{"id": user[0].id, "Name": user[0].Name, "phoneNumber": user[0].phoneNumber} for user in users]
    await socket_manager.emit('InitialData', userdata)
    db.close()
    
@socket_manager.on("pageRequest")
async def pageReq(sid,offset,limit):
    db = SessionLocal()
    skip=(offset-1)*limit
    query = text("SELECT * FROM user LIMIT :skip, :limit")
    data = db.execute(query, {'skip': skip, 'limit': limit})
    userdata = [{"id": user.id, "Name": user.Name, "phoneNumber": user.phoneNumber} for user in data]
    print("my user data:- ",userdata)
    await socket_manager.emit('PageRequestEmit', userdata)
    db.close()


# Define the event handler function
async def emit_binlog_event():
    db = SessionLocal()
    users = db.execute(select(User)).all()
    userdata = [{"id": user[0].id, "Name": user[0].Name, "phoneNumber": user[0].phoneNumber} for user in users]
    await socket_manager.emit('binlog_event', userdata) # emit to specific client
    db.close()
    # Emit the event to all connected clients
    # await app.sio.emit('binlog_event', )

def binlog_stream():
    stream = BinLogStreamReader(
        connection_settings=MYSQL_SETTINGS,
        server_id=100,  # Unique server ID
        only_schemas=['test'], #target specific database
        only_events=[DeleteRowsEvent, WriteRowsEvent, UpdateRowsEvent],
        blocking=True
    )
    
    db = SessionLocal()

    for binlogevent in stream:
        for row in binlogevent.rows:
            event = {"type": type(binlogevent).__name__, "row": row}
            asyncio.run(emit_binlog_event())
            print(event)  # Replace with your logic (e.g., broadcasting via WebSocket)

    db.close()
    stream.close()

threading.Thread(target=binlog_stream).start()

# FastAPI route to get user by ID
@app.get("/users/{user_id}")
async def read_user(user_id: int, db: Session = Depends(get_db)):
    user = db.execute(select(User).filter(User.id == user_id)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not foun")
    return {"id": user.id, "name": user.Name, "phonenumber": user.phoneNumber}

# New endpoint to get all users
@app.get("/users")
async def read_all_users(db: Session = Depends(get_db)):
    users = db.execute(select(User)).all()
    print(users)
    return [{"id": user[0].id, "Name": user[0].Name, "phoneNumber": user[0].phoneNumber} for user in users]