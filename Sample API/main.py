from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    text: str = "Your string here"
    is_done: bool = False

items = []

@app.get("/")
def root():
    return {"Hello": "World"}

@app.post("/items")
def create_item(item: Item) -> list[Item]:
    items.append(item)
    return items

@app.get("/items")
def create_item(limit: int = 10) -> list:
    return items[0:limit ]

@app.get("/item/{id}")
def get_item(id: int)-> Item:
    if id < len(items):
        return items[id]
    else:
        raise HTTPException(status_code=404,detail=f"Item {id} was not found")