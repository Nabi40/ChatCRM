from django.db import models


class UserProfile(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} <{self.email}>"
    

class Inventory(models.Model):
    product_code = models.CharField(max_length=100, unique=True)
    product_name = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product_name} ({self.product_code})"


class Order(models.Model):
    STATUS_CHOICES = [
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
        ("refunded", "Refunded"),
    ]

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="orders")
    order_id = models.CharField(max_length=50, unique=True)
    product = models.ForeignKey(Inventory, on_delete=models.CASCADE, related_name="orders")
    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="processing")
    delivery_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.order_id
    
class RefundRequest(models.Model):
    STATUS_CHOICES = [
        ("requested", "Requested"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("completed", "Completed"),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="refunds")
    reason = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="requested")
    created_at = models.DateTimeField(auto_now_add=True)


class Complaint(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="complaints")
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, blank=True, null=True, related_name="complaints")
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class ChatSession(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="chat_sessions")
    session_key = models.CharField(max_length=100, unique=True)
    current_order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    last_intent = models.CharField(max_length=50, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.session_key


class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
    ]

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
            ordering = ["created_at", "id"]