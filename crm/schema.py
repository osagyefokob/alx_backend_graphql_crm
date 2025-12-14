import re
import graphene
from graphene_django import DjangoObjectType
from django.db import transaction
from .models import Customer, Product, Order


class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer


class ProductType(DjangoObjectType):
    class Meta:
        model = Product


class OrderType(DjangoObjectType):
    class Meta:
        model = Order


class CreateCustomer(graphene.Mutation):
    customer = graphene.Field(CustomerType)
    message = graphene.String()

    class Arguments:
        name = graphene.String(required=True)
        email = graphene.String(required=True)
        phone = graphene.String()

    def mutate(self, info, name, email, phone=None):
        if Customer.objects.filter(email=email).exists():
            raise Exception("Email already exists")

        if phone and not re.match(r"^(\+\d{10,15}|\d{3}-\d{3}-\d{4})$", phone):
            raise Exception("Invalid phone format")

        customer = Customer.objects.create(
            name=name,
            email=email,
            phone=phone
        )
        return CreateCustomer(customer=customer, message="Customer created successfully")


class BulkCreateCustomers(graphene.Mutation):
    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

    class Arguments:
        input = graphene.List(
            graphene.NonNull(
                graphene.InputObjectType(
                    "CustomerInput",
                    name=graphene.String(required=True),
                    email=graphene.String(required=True),
                    phone=graphene.String()
                )
            )
        )

    def mutate(self, info, input):
        created = []
        errors = []

        with transaction.atomic():
            for data in input:
                try:
                    if Customer.objects.filter(email=data.email).exists():
                        raise Exception("Duplicate email")

                    customer = Customer.objects.create(
                        name=data.name,
                        email=data.email,
                        phone=data.phone
                    )
                    created.append(customer)
                except Exception as e:
                    errors.append(str(e))

        return BulkCreateCustomers(customers=created, errors=errors)


class CreateProduct(graphene.Mutation):
    product = graphene.Field(ProductType)

    class Arguments:
        name = graphene.String(required=True)
        price = graphene.Float(required=True)
        stock = graphene.Int()

    def mutate(self, info, name, price, stock=0):
        if price <= 0:
            raise Exception("Price must be positive")
        if stock < 0:
            raise Exception("Stock cannot be negative")

        product = Product.objects.create(
            name=name,
            price=price,
            stock=stock
        )
        return CreateProduct(product=product)


class CreateOrder(graphene.Mutation):
    order = graphene.Field(OrderType)

    class Arguments:
        customer_id = graphene.ID(required=True)
        product_ids = graphene.List(graphene.ID, required=True)

    def mutate(self, info, customer_id, product_ids):
        if not product_ids:
            raise Exception("At least one product is required")

        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            raise Exception("Invalid customer ID")

        products = Product.objects.filter(id__in=product_ids)
        if products.count() != len(product_ids):
            raise Exception("Invalid product ID")

        total = sum([p.price for p in products])

        order = Order.objects.create(
            customer=customer,
            total_amount=total
        )
        order.products.set(products)

        return CreateOrder(order=order)


class Query(graphene.ObjectType):
    pass


class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()
