# users/urls.py
from django.urls import path
from .views import (create_chat_room, get_chat_room, get_messages, get_patient_appointments, save_message, signup, login, logout, check_auth, 
                    medicinal_item_list_create, medicinal_item_detail, fetch_all_doctors, 
                    add_to_cart, fetch_category_items, add_doctor_profile, fetch_doctor_profile, 
                    checkout_cart, get_user_orders, get_cart_items, request_appointment, get_doctor_appointments,
                    update_appointment_status, search_medicine, upload_patient_bill, verify_doctor_by_admin)

urlpatterns = [
    path('signup/', signup, name='signup'),
    path('login/', login, name='login'),
    path('logout/', logout, name='logout'),
    path('check-auth/', check_auth, name='check_auth'),
    path('medicinal-items/', medicinal_item_list_create, name='medicinal-item-list-create'),
    path('medicinal-items/<str:pk>/', medicinal_item_detail, name='medicinal-item-detail'),
    path('medicinal/<str:category>/', fetch_category_items, name='fetch_category_items'),
    path('doctors/', fetch_all_doctors, name='fetch-all-doctors'),
    path('add-to-cart/',add_to_cart, name='add_to_cart'),
    path('get-cart-items/', get_cart_items, name="get_cart_items"),
    path('checkout/', checkout_cart, name="checkout_cart"),
    path('user-orders/', get_user_orders, name='get-user-orders'),
    path('doctors/create/', add_doctor_profile, name='create_doctor'),
    path('doctors/<str:user_id>/', fetch_doctor_profile, name='get_doctors'),
    path('verify/doctors/<str:user_id>/', verify_doctor_by_admin, name='verify_doctor_by_admin'),
    path('request-appointment/', request_appointment, name='request-appointment'),
    path('doctor-appointments/', get_doctor_appointments, name='get-doctor-appointments'),
    path('update-appointment-status/', update_appointment_status, name='update-appointment-status'),
    path('search-medicine/', search_medicine, name='search-medicine'),
    path('create-chat-room/', create_chat_room, name='create_chat_room'),
    path('get-chat-room/<str:user1_id>/<str:user2_id>', get_chat_room, name='get_chat_room'),
    path('save-message/', save_message, name='save_message'),
    path('get-messages/<str:room_id>/', get_messages, name='get_messages'),
    path('patient-appointments/', get_patient_appointments, name='get_patient_appointments'),
    path('upload-bill/', upload_patient_bill, name='upload_patient_bill'),
]
