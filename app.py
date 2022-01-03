from flask import Flask
from flask_restful import Api, Resource, reqparse, abort, fields, marshal_with
import psycopg2
from psycopg2 import Error
import signal
import parsers
import sys
import queries
import datetime

def date_splitter(s):
    tab = s.split('-')
    return datetime.datetime(int(tab[0]), int(tab[1]), int(tab[2]))   

def shutdown(signal_received, frame):
    cursor.close()
    connection.close()
    print("REST api has been shut down")
    exit(0)

signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT, shutdown)

app = Flask(__name__)
#app.secret_key = "siemaeniuwpuscmnie"
api = Api(app)

try:
    connection = psycopg2.connect(user="postgres",
                                  password="postgres",
                                  host="127.0.0.1",
                                  port="5432",
                                  database="coffin_factory")

    cursor = connection.cursor()

except (Exception, Error) as error:
    print("Error while connecting to PostgreSQL", error)

def print_psycopg2_exception(err):
    err_type, err_obj, traceback = sys.exc_info()
    line_num = traceback.tb_lineno
    print ("\npsycopg2 ERROR:", err, "on line number:", line_num)
    print ("psycopg2 traceback:", traceback, "-- type:", err_type)
    print ("\nextensions.Diagnostics:", err.diag)
    print ("pgerror:", err.pgerror)
    print ("pgcode:", err.pgcode, "\n")
    return err.pgcode, err.pgerror

class Employee(Resource):
    def post(self):
        parser = parsers.employee_parser()
        args = parser.parse_args()
        query = queries.employee_query(args)
        cursor.execute(query)
        connection.commit()
        return {}, 201
class Attendance(Resource):
    def post(self):
        parser = parsers.attendance_parser()
        args = parser.parse_args()
        query = queries.attendance_query(args)
        cursor.execute("SELECT id_employee FROM employee WHERE id_employee = {id_employee}".format(id_employee = args['id_employee']))
        if(cursor.fetchall() == []):
            return {'error' : 'There is no employee with given id'},404
        else:
            date_emp = cursor.fetchall()[0][0]
            date_att = date_splitter(args['attendance_date'])
            if(date_emp > date_att):
                return {"error" : "date employed can't be further than attendance date"}, 409
            try:
                cursor.execute(query)
                connection.commit()
            except Exception as err:
                code, error = print_psycopg2_exception(err)
                connection.rollback()
                if(code == "23505"):
                    return {"error" : "Unique Violation - given record already exists"}, 409
                else:
                    return {"error" : error, "code" : code}, 400
            return {}, 201
class Contractor(Resource):
    def post(self):
        parser = parsers.contractor_parser()
        args = parser.parse_args()
        query = queries.contractor_query(args)
        cursor.execute(query)
        connection.commit()
        return {}, 201
class Supplier(Resource):
    def post(self):
        parser = parsers.supplier_parser()
        args = parser.parse_args()
        query = queries.supplier_query(args)
        cursor.execute(query)
        connection.commit()
        return {}, 201
class Model(Resource):
    def post(self):
        parser = parsers.model_parser()
        args = parser.parse_args()
        if(args['available'] != "Y" and args['available'] != "N"):
            return {"error" : "available parameter can only have value Y if product is available and N if not"},400
        query = queries.model_query(args)
        cursor.execute("SELECT name_material FROM material WHERE name_material = '{name_material}'".format(name_material = args['name_material']))
        if(cursor.fetchall() == []):
            return {'error' : 'There is no material with given name'},404
        else:
            cursor.execute(query)
            connection.commit()
            return {}, 201
class Material(Resource):
    def post(self):
        parser = parsers.material_parser()
        args = parser.parse_args()
        query = queries.material_query(args)
        try:
            cursor.execute(query)
            connection.commit()
        except Exception as err:
            code, error = print_psycopg2_exception(err)
            connection.rollback()
            if(code == "23505"):
                return {"error" : "Unique Violation - given record already exists"}, 409
            else:
                return {"error" : error, "code" : code}, 400
        return {}, 201
class Delivery(Resource):
    def post(self):
        parser = parsers.delivery_parser()
        args = parser.parse_args()
        query = queries.delivery_query(args)
        cursor.execute("SELECT id_employee FROM employee join attendance using(id_employee) WHERE id_employee = {id_employee} AND attendance_date = '{attendance_date}'".format(id_employee = args['id_employee'], attendance_date = args['date_delivery']))
        employee = cursor.fetchall()
        cursor.execute("SELECT id_supplier FROM supplier WHERE id_supplier = {id_supplier}".format(id_supplier = args['id_supplier']))
        supplier = cursor.fetchall()
        if(employee == []):
            return {'error' : 'There is no employee with given id present on the day of the delivery'},404
        elif(supplier == []):
            return {'error' : 'There is no supplier with given id'},404
        else:
            date_emp = cursor.fetchall()[0][0]
            date_del = date_splitter(args['date_delivery'])
            if(date_emp > date_del):
                return {"error" : "date employed can't be further than delivery date"}, 409
            cursor.execute(query)
            connection.commit()
            return {}, 201
class Order_component(Resource):
    def post(self):
        parser = parsers.order_component_parser()
        args = parser.parse_args()
        query = queries.order_component_query(args)
        cursor.execute("SELECT id_order FROM orders WHERE id_order = {id_order}".format(id_order = args['id_order']))
        order = cursor.fetchall()
        cursor.execute("SELECT id_model FROM model WHERE id_model = {id_model}".format(id_model = args['id_model']))
        model = cursor.fetchall()
        if(order == []):
            return {'error' : 'There is no order with given id'},404
        elif(model == []):
            return {'error' : 'There is no model with given id'},404
        else:
            try:
                cursor.execute(query)
                connection.commit()
            except Exception as err:
                code, error = print_psycopg2_exception(err)
                connection.rollback()
                if(code == "23505"):
                    return {"error" : "Unique Violation - given record already exists"}, 409
                else:
                    return {"error" : error, "code" : code}, 400
            return {}, 201
class Stock(Resource):
    def post(self):
        parser = parsers.stock_parser()
        args = parser.parse_args()
        query = queries.stock_query(args)
        cursor.execute("SELECT name_material FROM material WHERE name_material = '{name_material}'".format(name_material = args['name_material']))
        material = cursor.fetchall()
        cursor.execute("SELECT id_delivery FROM delivery WHERE id_delivery = {id_delivery}".format(id_delivery = args['id_delivery']))
        delivery = cursor.fetchall()
        if(material == []):
            return {'error' : 'There is no delivery with given id'},404
        elif(delivery == []):
            return {'error' : 'There is no material with given name'},404
        else:
             try:
                cursor.execute(query)
                connection.commit()
             except Exception as err:
                code, error = print_psycopg2_exception(err)
                connection.rollback()
                if(code == "23505"):
                    return {"error" : "Unique Violation - given record already exists"}, 409
                else:
                    return {"error" : error, "code" : code}, 400
             return {}, 201
class Orders(Resource):
    def post(self):
        parser = parsers.orders_parser()
        args = parser.parse_args()
        query = queries.orders_query(args)
        cursor.execute("SELECT id_contractor FROM contractor WHERE id_contractor = {id_contractor}".format(id_contractor = args['id_contractor']))
        if(cursor.fetchall() == []):
            return {'error' : 'There is no contractor with given id'},404
        else:
            if(not('date_finished' not in args or args['date_finished'] == None)):
                date_sta = date_splitter(args['date_order'])
                date_fin = date_splitter(args['date_finished'])
                if(date_sta > date_fin):
                    return {"error" : "date employed can't be further than attendance date"}, 409
            cursor.execute(query)
            connection.commit()
            return {}, 201

api.add_resource(Employee, "/employee")
api.add_resource(Attendance, "/attendance")
api.add_resource(Contractor, "/contractor")
api.add_resource(Supplier, "/supplier")
api.add_resource(Model, "/model")
api.add_resource(Material, "/material")
api.add_resource(Delivery, "/delivery")
api.add_resource(Order_component, "/order_component")
api.add_resource(Stock, "/stock")
api.add_resource(Orders, "/orders")

if __name__ == "__main__":
	app.run(debug=True)