import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

class DatabaseAdmin:
    def __init__(self, service_account_json: str):
        cred = credentials.Certificate(service_account_json)
        firebase_admin.initialize_app(cred)
        self.m_db = firestore.client()

    def get_collection(self, path: str):
        return self.m_db.collection(path)
    
    def get_document(self, path: str):
        return self.m_db.document(path)
    
    def set_document(self, path: str, data: dict):
        self.m_db.document(path).set(data)

    def update_document(self, path: str, data: dict):
        self.m_db.document(path).update(data)

    def delete_document(self, path: str):
        self.m_db.document(path).delete()
        
# # testing
# if __name__ == "__main__":
#     db_admin = DatabaseAdmin(".environment/linkedin-automation-401619-5d531a7232e5.json")

#     # try get_collection
#     test1 = db_admin.get_collection("test1")
#     print(test1.get())
#     test3 = db_admin.get_collection("test1/test2/test3")
#     print(test3.get())

#     # try get_document
#     test2 = db_admin.get_document("test1/test2")
#     print(test2.get().to_dict())
#     test4 = db_admin.get_document("test1/test2/test3/test4")
#     print(test4.get().to_dict())

#     # try set_document
#     db_admin.set_document("test1/test2/test3/test5", {"test": "test"})
#     test5 = db_admin.get_document("test1/test2/test3/test5")
#     print(test5.get().to_dict())

#     # try update_document
#     db_admin.update_document("test1/test2/test3/test5", {"test": "test2"})
#     test5 = db_admin.get_document("test1/test2/test3/test5")
#     print(test5.get().to_dict())

#     # try delete_document
#     db_admin.delete_document("test1/test2/test3/test5")
#     test5 = db_admin.get_collection("test1/test2/test3")
#     documents = test5.stream()
#     for document in documents:
#         print(f"{document.id} => {document.to_dict()}")