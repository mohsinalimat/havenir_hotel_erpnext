# -*- coding: utf-8 -*-
# Copyright (c) 2020, Havenir and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class HotelCheckOut(Document):
    def validate(self):
        room_doc = frappe.get_doc('Rooms', self.room)
        if room_doc.room_status != 'Checked In':
            frappe.throw('Room Status is not Checked In')
    def on_submit(self):
        room_doc = frappe.get_doc('Rooms',self.room)
        room_doc.db_set('room_status','Available')
        check_in_doc = frappe.get_doc('Hotel Check In',self.check_in_id)
        all_checked_out = 1

        # Setting Food Orders to Complete
        room_food_order_list = frappe.get_list('Room Food Order', filters={
            'status': 'To Check Out',
            'room': self.room,
            'check_in_id': self.check_in_id
        })

        for food_order in room_food_order_list:
            food_order_doc = frappe.get_doc('Room Food Order', food_order.name)
            food_order_doc.db_set('status','Completed')

        # Setting Laundry Orders to Complete
        room_laundry_order_list = frappe.get_list('Room Laundry Order', filters={
            'status': 'To Check Out',
            'room': self.room,
            'check_in_id': self.check_in_id
        })

        for laundry_order in room_laundry_order_list:
            laundry_order_doc = frappe.get_doc('Room Laundry Order', laundry_order.name)
            laundry_order_doc.db_set('status','Completed')

        # Setting Check In doc to Complete
        for room in check_in_doc.rooms:
            if frappe.db.get_value('Rooms',room.room_no,'room_status') == 'Checked In':
                all_checked_out = 0
        if all_checked_out == 1:
            check_in_doc.db_set('status','Completed')

        # Creating Addtion Hotel Payment Vouchers
        if self.net_balance_amount > 0 and self.customer == 'Hotel Walk In Customer':
            payment_doc = frappe.new_doc('Hotel Payment Entry')
            payment_doc.room = self.room
            payment_doc.amount_paid = self.net_balance_amount
            payment_doc.guest_id = self.guest_id
            payment_doc.check_in_id = self.check_in_id
            payment_doc.guest_name = self.guest_name
            payment_doc.save()
            payment_doc.submit()
        
        
        

    def get_check_in_details(self):
        room_doc = frappe.get_doc('Rooms', self.room)
        check_in_doc = frappe.get_doc('Hotel Check In', room_doc.check_in_id)
        return [check_in_doc.name, check_in_doc.cnic, check_in_doc.guest_name, check_in_doc.check_in, check_in_doc.contact_no, check_in_doc.guest_id]

    def calculate_stay_days(self):
        if frappe.utils.data.date_diff(self.check_out, self.check_in) == 0:
            return 1
        else:
            return frappe.utils.data.date_diff(self.check_out, self.check_in)

    def get_items(self):
        # Getting Hotel Check In Details
        hotel_check_in = frappe.get_doc('Hotel Check In', self.check_in_id)
        check_in_dict = {}
        for room in hotel_check_in.rooms:
            if room.room_no == self.room:
                check_in_dict['room'] = room.room_no
                check_in_dict['price'] = room.price

        # Geting Room Food Order Details
        food_order_list = []
        room_food_order_list = frappe.get_list('Room Food Order', filters={
            'status': 'To Check Out',
            'room': self.room,
            'check_in_id': self.check_in_id
        })
        for food_order in room_food_order_list:
            food_order_dict = {}
            food_order_doc = frappe.get_doc('Room Food Order', food_order.name)
            food_order_dict['name'] = food_order_doc.name
            food_order_dict['date'] = food_order_doc.posting_date
            food_order_dict['source'] = food_order_doc.source
            food_order_dict['items'] = []
            # Looping through items
            for item in food_order_doc.items:
                food_item_dict = {}
                food_item_dict['item'] = item.item
                food_item_dict['qty'] = item.qty
                food_item_dict['rate'] = item.rate
                food_item_dict['amount'] = item.amount
                food_order_dict['items'].append(food_item_dict)
            food_order_list.append(food_order_dict)

        # Getting Room Laundry Order Details
        laundry_order_list = []
        room_laundry_order_list = frappe.get_list('Room Laundry Order', filters={
            'status': 'To Check Out',
            'room': self.room,
            'check_in_id': self.check_in_id
        })
        for laundry_order in room_laundry_order_list:
            laundry_order_dict = {}
            laundry_order_doc = frappe.get_doc(
                'Room Laundry Order', laundry_order.name)
            laundry_order_dict['name'] = laundry_order_doc.name
            laundry_order_dict['date'] = laundry_order_doc.posting_date
            laundry_order_dict['source'] = laundry_order_doc.source
            laundry_order_dict['items'] = []
            # Looping through items
            for item in laundry_order_doc.items:
                laundry_item_dict = {}
                laundry_item_dict['item'] = item.item
                laundry_item_dict['qty'] = item.qty
                laundry_item_dict['rate'] = item.rate
                laundry_item_dict['amount'] = item.amount
                laundry_order_dict['items'].append(laundry_item_dict)
            laundry_order_list.append(laundry_order_dict)
        stay_days = frappe.utils.data.date_diff(self.check_out, self.check_in)

        # Getting Payments
        payment_entry_list = []
        room_payment_entry_list = frappe.get_list('Hotel Payment Entry',filters={
            'check_in_id' : self.check_in_id,
            'docstatus': 1
        }, order_by='name asc')

        for payment in room_payment_entry_list:
            payment_entry_dict = {}
            payment_doc = frappe.get_doc('Hotel Payment Entry', payment)
            payment_entry_dict['payment_entry'] = payment_doc.name
            payment_entry_dict['amount_paid'] = payment_doc.amount_paid
            payment_entry_dict['posting_date'] = payment_doc.posting_date
            payment_entry_list.append(payment_entry_dict)

        return [stay_days, check_in_dict, food_order_list, laundry_order_list, payment_entry_list]
