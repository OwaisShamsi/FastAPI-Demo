from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, String, select, update
from sqlalchemy.ext.declarative import declarative_base
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel



# Database settings
# DATABASE_URL = "mssql+pyodbc://sa:root123@LP120\\SQLEXPRESS/test?driver=ODBC+Driver+17+for+SQL+Server"
DATABASE_URL = "mysql+mysqlconnector://root:root@localhost:3306/school"

# SQLAlchemy models
Base = declarative_base()

class Teacher(Base):
    __tablename__ = "teachers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String)

class PostTeacher(BaseModel):
    name:str = None
    email:str = None

class Token(BaseModel):
    access_token: str
    token_type: str 
    

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

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db    
    finally:
        db.close()

# FastAPI route to get all Teachers
@app.get("/teachers")
async def read_all_teachers(db: Session = Depends(get_db)):
    teachers = db.execute(select(Teacher)).all()
    print(teachers)
    if teachers is None:
        raise HTTPException(status_code=404, detail="Teachers not found")
    teachers_data = [{"id":teacher[0].id,"name":teacher[0].name,"email":teacher[0].email} for teacher in teachers]
    return teachers_data

# FastAPI route to get Teacher by id
@app.get("/teacher/{teacher_id}")
async def read_teacher(teacher_id: int, db: Session = Depends(get_db)):
    teacher = db.execute(select(Teacher).filter(Teacher.id == teacher_id)).scalar_one_or_none()
    if teacher is None:
        raise HTTPException(status_code=404, detail=f"Teacher with id {teacher_id} was not found")
    return {"id": teacher.id,"name":teacher.name,"email":teacher.email}

# FastAPI route to post Teacher
@app.post("/teacher")
async def post_teacher(teacher_data: PostTeacher,db: Session = Depends(get_db)):
    # Check if teacher with the same email already exists1
    existing_teacher = db.execute(select(Teacher).filter(Teacher.name == teacher_data.name)).scalar_one_or_none()
    if existing_teacher:
        raise HTTPException(status_code=400, detail=f"Teacher with name {teacher_data.name} already exists")
     # Create a new teacher
    new_teacher = Teacher(name=teacher_data.name, email=teacher_data.email)
    db.add(new_teacher)
    db.commit()
    db.refresh(new_teacher)
    return {"id": new_teacher.id, "name": new_teacher.name, "email": new_teacher.email}

# FastAPI route to put Teacher
@app.put("/teacher")
async def put_teacher(teacher_id: int, teacher_data: PostTeacher,db: Session = Depends(get_db)):
    teacher = db.execute(select(Teacher).filter(Teacher.id == teacher_id)).scalar_one_or_none()
     # Update existing teacher with id
    if teacher_data.name is None:
        print("name is none")
        teacher_data.name = teacher.name
    if teacher_data.email is None:
        teacher_data.email = teacher.email
    update_stmt = update(Teacher).where(Teacher.id == teacher_id).values(name = teacher_data.name,email = teacher_data.email)
    db.execute(update_stmt)
    db.commit()
    return {"message": f"Teacher with id {teacher_id} has been updated"}    