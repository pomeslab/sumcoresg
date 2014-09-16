from flaskext.script import Manager
from app_config import db, app
from sumcoresg import start_collecting_data

manager = Manager(app)

@manager.command
def createdbschema():
    db.create_all()

@manager.command
def createdbschema_figure():
    from db_tables import Figure
    Figure.metadata.create_all(db.engine)

@manager.command
def start_collecting():
    start_collecting_data()
    
if __name__ == "__main__":
    manager.run()
