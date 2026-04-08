from django.contrib import admin
from .models import UserProfile, Inventory, Order, RefundRequest, Complaint, ChatSession, ChatMessage

admin.site.register(UserProfile)
admin.site.register(Inventory)
admin.site.register(Order)
admin.site.register(RefundRequest)
admin.site.register(Complaint)
admin.site.register(ChatSession)
admin.site.register(ChatMessage)