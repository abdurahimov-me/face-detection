from datetime import datetime

from django.core.management.base import BaseCommand
from django.db.models import OuterRef, Subquery, Q, Exists

from ....products.models import Product, ProductSimilarity

NOT_GENERATING = -1
GENERATING = 0
MODERATING = 1
APPROVED = 2
REJECTED = 3
ACADEMIC = 1
PERSONAL = 2

AKE_IDS = (111, 295, 2115)
EXCLUDE_OWNERS = (5755, 5233, 295, 111, 2115, 39710)


class ApproveCommand(BaseCommand):

    def handle(self, *args, **options):
        # Product.objects.filter(status=GENERATING).update(status=NOT_GENERATING)
        sub_pages = ProductSimilarity.objects.filter(product=OuterRef("pk")).values("similar__pages").order_by("id")[:1]
        sub_size = ProductSimilarity.objects.filter(product=OuterRef("pk")).values("similar__size").order_by("id")[:1]
        same_pair_exists = Product.objects.filter(name=OuterRef('name')).exclude(pk=OuterRef('pk'))
        products = Product.objects.filter(pages__in=(1, 2), owner_id__in=(111, 295), status=APPROVED)
        products = (
            Product.objects
            .annotate(
                similarity=Subquery(
                    ProductSimilarity.objects
                    .filter(product_id=OuterRef('id'), similar__deleted=False)
                    .order_by('-similarity')
                    .values('similarity')[:1]
                ),
                # sub_pages=Subquery(sub_pages),
                # sub_size=Subquery(sub_size),
                # same_pair_exists=Exists(same_pair_exists),
            )
            .filter(
                # Q(similarity__lte=97) | Q(similarity__isnull=True),
                status=MODERATING, deleted=False, content_type=ACADEMIC,
            )
            .exclude(owner_id__in=EXCLUDE_OWNERS)
        )
        # self.stdout.write(f'Total products in moderating status without similarity: {products.count()}')

        same_pair_exists = (Product.objects
                            .filter(
            pages=OuterRef('pages'),
            ext=OuterRef('ext'),
            size=OuterRef('size'),
        ).exclude(pk=OuterRef('pk')))

        products = (
            Product.objects
            .annotate(
                similarity=Subquery(
                    ProductSimilarity.objects
                    .filter(product_id=OuterRef('id'), product__deleted=False)
                    .order_by('-similarity')
                    .values('similarity')[:1]
                ),
                has_same_pair=Exists(same_pair_exists),
            )
            .filter(
                similarity=100,
                has_same_pair=True,
                status=MODERATING,
                size__isnull=False,
            )
        )
