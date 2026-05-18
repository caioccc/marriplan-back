from django.core.management.base import BaseCommand
from django.utils.text import slugify
from app.models import SupplierCategory, Supplier  # Altere 'seu_app' para o nome do seu app

class Command(BaseCommand):
    help = "Gera a lista interna de categorias e 50 fornecedores reais de Campina Grande e região"

    def handle(self, *args, **options):
        # 1. Garantir que as categorias existam
        categories_list = [
            'Buffet', 'Cerimonial', 'Fotografia', 'Filmagem', 'Música',
            'Decoração', 'Espaço', 'Convites', 'Bolo', 'Doces', 'Vestido', 'Lua de mel'
        ]
        
        category_objects = {}
        for cat_name in categories_list:
            category, created = SupplierCategory.objects.get_or_create(
                name=cat_name,
                defaults={'slug': slugify(cat_name)}
            )
            category_objects[cat_name] = category
            if created:
                self.stdout.write(self.style.SUCCESS(f"Categoria criada: {cat_name}"))

        suppliers_data = [
            # --- Buffet ---
            {"name": "Le mel buffet e eventos", "category": "Buffet", "city": "Campina Grande", "state": "Paraíba", "phone": "(83) 98855-2219", "whatsapp": "+5583988552219", "instagram": "https://www.instagram.com/lemelbuffeteeventos/",
             "address": "R. José Gonçalves de Melo, 52 - Universitário, Campina Grande - PB, 58429-085", "cover_image_url": "https://res.cloudinary.com/freelancerinc/image/upload/v1778952063/le_mel_ocdobe.jpg"},
            {"name": "Regallier Buffet", "category": "Buffet", "city": "Campina Grande", "state": "Paraíba", "phone": "(83) 99145-8987", "whatsapp": "+5583991458987", "instagram": "https://www.instagram.com/regallierbuffet/",
             "address": "R. Antônio Joaquim Pequeno, 198 - Universitário, Campina Grande - PB, 58429-010", "cover_image_url": "https://res.cloudinary.com/freelancerinc/image/upload/v1778952063/385343367_697956448457320_3321118921925238988_n_g6cdvk.jpg"},
            {"name": "Buffet Santana", "category": "Buffet", "city": "Campina Grande", "state": "Paraíba", "phone": "(83) 99837-0099", "whatsapp": "+5583998370099", "instagram": "https://www.instagram.com/buffetsantana_cg/",
             "address": "R. Damasco, 350 - Santa Rosa, Campina Grande - PB, 58416-580", "cover_image_url": "https://res.cloudinary.com/freelancerinc/image/upload/v1778952063/65126444_1676465889163900_2173456685333479424_n_ywwsvu.jpg"},

            # --- Cerimonial ---
            {"name": "Neide Cerimonial E Eventos", "category": "Cerimonial", "city": "Campina Grande", "state": "Paraíba", "phone": "(83) 99991-0326", "whatsapp": "+5583999910326", "website": "https://www.casamentos.com.br/cerimonialista/neide-cerimonial-e-eventos--e120424",
              "instagram": "https://www.instagram.com/neidefreitascerimonial/",  "address": "R. João da Mata, 407 - SALA 101 - Centro, Campina Grande - PB, 58400-245", "cover_image_url": "https://res.cloudinary.com/freelancerinc/image/upload/v1778952435/55aa5841-c5f3-4549-a646-ee764488ba12_WhatsApp-Image-2024-05-14-at-12.43.41_m0pe3a.webp"},
            {"name": "Tulip Cerimoniais", "category": "Cerimonial", "city": "Campina Grande", "state": "Paraíba", "phone": "(83) 98874-9169", "whatsapp": "+558388749169", 
             "instagram": "https://www.instagram.com/tulipcerimoniais/", "address": "R. João da Mata, 407 - SALA 101 - Centro, Campina Grande - PB, 58400-245", "cover_image_url": "https://res.cloudinary.com/freelancerinc/image/upload/v1778952540/555444643_18431415187100249_7666184394088624231_n_m0lb1t.jpg"},
            # --- Fotografia ---
            
            # --- Filmagem ---
            
            # --- Música ---
            
            # --- Decoração ---
            
            # --- Espaço ---
            
            # --- Convites ---
            {"name": "Papyrus Ateliê", "category": "Convites", "city": "Campina Grande", "state": "Paraíba", "phone": "(83) 99144-2769", "whatsapp": "+5583991442769", "instagram": "https://www.instagram.com/papyrusatelie/",
             "address": "R. Acre, 225 - Liberdade, Campina Grande - PB, 58414-260", "cover_image_url": "https://res.cloudinary.com/freelancerinc/image/upload/v1779104874/Design_sem_nome_1_zoy6vi.jpg"},

            # --- Bolo ---
            
            # --- Doces ---
            
            # --- Vestido ---
            
            # --- Lua de mel ---
        ]

        # 3. Inserir Fornecedores garantindo a não-duplicação
        created_count = 0
        for supplier_info in suppliers_data:
            category_obj = category_objects[supplier_info["category"]]
            
            # Usa name + category para checar a existência
            supplier, created = Supplier.objects.get_or_create(
                name=supplier_info["name"],
                category=category_obj,
                defaults={
                    "city": supplier_info["city"],
                    "state": "PB",
                    "status": Supplier.STATUS_APPROVED,  # Já cria aprovado por padrão
                    "description": f"Fornecedor de {supplier_info['category']} localizado em {supplier_info['city']} - PB.",
                    "phone": supplier_info.get("phone", ""),
                    "whatsapp": supplier_info.get("whatsapp", ""),
                    "instagram": supplier_info.get("instagram", ""),
                    "address": supplier_info.get("address", ""),
                    "cover_image_url": supplier_info.get("cover_image_url", ""),
                    "website": supplier_info.get("website", ""),
                }
            )
            
            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Processo concluído! {created_count} novos fornecedores foram adicionados à base."
        ))