from RPA.Database import Database
import erppeek

# Variables
# odoo settings
odoo_server = 'https://ibassoftware-integreationtest.odoo.com/'
odoo_database = 'ibassoftware-integreationtest-production-4639329'
odoo_username = "admin"
odoo_password = "123"
VAT_Tax_ID = 3
odoo_account_receivable_id = 6
odoo_account_payable_id = 14

# IBAS DATABASE
COMPANY_OID_IN_IBAS = "0da5cd6a-3719-48c0-a676-a7bc25ac7234"

# MYSQL Settings
mysql_database_name = "jolliantreopened"
mysql_username = "root"
mysql_password = ""
mysql_host = "localhost"


def sync_ibas_products(db, client):

    ibas_products = db.query(
        "select * from product where OdooDatabaseID IS NULL" +
        " OR OdooDatabaseID = 0")

    for product in ibas_products:
        odoo_id = sync_product_in_odoo(product, client)
        # Update product with odoo id
        sql = "UPDATE product SET OdooDatabaseID = " + \
            str(odoo_id) + " WHERE Oid = '" + product['Oid'] + "'"

        db.query(sql)

        print('Created Product in Odoo ' + str(product['ProductName']))

    return


def sync_product_in_odoo(product, client):
    # Create odoo product here and return odoo ID
    params = {
        'name': product['ProductName'],
        'type': 'service',
        'categ_id': 1,
        'purchase_ok': True,
        'sale_ok': True
    }
    odoo_id = client.create('product.product', params)

    return odoo_id


def sync_vendor_in_odoo(vendor, client):
    params = {
        'company_type': 'company',
        'name': vendor['VendorName'],
        'property_account_receivable_id': odoo_account_receivable_id,
        'property_account_payable_id': odoo_account_receivable_id,
    }
    odoo_id = client.create('res.partner', params)

    return odoo_id


def sync_ibas_vendors(db, client):

    ibas_vendors = db.query(
        "select * from vendor where OdooID IS NULL" +
        " OR OdooID = 0")

    for vendor in ibas_vendors:
        odoo_id = sync_vendor_in_odoo(vendor, client)
        # Update product with odoo id
        sql = "UPDATE vendor SET OdooID = " + \
            str(odoo_id) + " WHERE Oid = '" + vendor['Oid'] + "'"

        db.query(sql)

        print('Created Vendor in Odoo ' + str(vendor['VendorName']))

    return


def create_purchase_order_in_odoo(db, client, po):

    # Get vendor odoo ID from ibas
    ibas_vendor_id = 0
    ibas_vendors = db.query(
        "select * from vendor where Oid = '" + str(po["Vendor"]) + "'")

    for vendor in ibas_vendors:
        ibas_vendor_id = vendor["OdooID"]
        break

    params = {
        'partner_id': ibas_vendor_id,
        'name': po['PurchaseOrderNumber'],
        'date_order': str(po['PurchaseOrderDate'].date())
    }
    odoo_id = client.create('purchase.order', params)

    return odoo_id


def sync_purchase_orders(db, client):
    #  Get All Purchases where odoo id is none or 0 and status = 1 and oid is equal to company oid
    ibas_purchase_orders = db.query(
        "select * from purchaseorder where OdooID IS NULL AND STATUS = 1 AND Company = '" + COMPANY_OID_IN_IBAS + "'" +
        " OR OdooID = 0 AND STATUS = 1 AND Company = '" + COMPANY_OID_IN_IBAS + "'")

    for po in ibas_purchase_orders:
        # Create Purchase Order

        odoo_po_id = create_purchase_order_in_odoo(db, client, po)
        # Create Purchase Order Lines
        create_purchase_order_lines(db, client, odoo_po_id, po)
        print("Created PO " + str(po["PurchaseOrderNumber"]))

        # confirm purchase order
        # update IBAS

        sql = "UPDATE purchaseorder SET OdooID = " + \
            str(odoo_po_id) + " WHERE Oid = '" + po['Oid'] + "'"
        db.query(sql)

        client.execute_kw('purchase.order', 'button_confirm', [odoo_po_id])

    return


def create_purchase_order_lines(db, client, odoo_po_id, po):

    vat_id = [(4, VAT_Tax_ID)]
    if po['VATApplies'] == b'\x01':
        print("This PO has VAT")
    else:
        print("NO VAT")
        vat_id = []

    ibas_purchase_order_lines = db.query(
        "select * from purchaseorderline where PurchaseOrder = '" +
        po['Oid'] + "'")

    for pol in ibas_purchase_order_lines:
        # Get product odoo ID
        this_product_odoo_id = get_ibas_product_odoo_id(pol["Product"], db)

        params = {
            'product_id': this_product_odoo_id,
            'name': po['PurchaseOrderNumber'],
            'product_qty': pol['Quantity'],
            'price_unit': float(pol['LineTotal']) / float(pol['Quantity']),
            'order_id': odoo_po_id,
            'taxes_id': vat_id
        }

        # Get VAT

        # Create purchase order line in odoo

        client.create('purchase.order.line', params)

    return


def get_ibas_product_odoo_id(product_oid, db):
    products_res = db.query(
        "select * from product where Oid = '" + product_oid + "'")
    for x in products_res:
        return x['OdooDatabaseID']


def minimal_task():

    client = erppeek.Client(
        server=odoo_server,
        db=odoo_database,
        user=odoo_username,
        password=odoo_password
    )

    db = Database()
    db.connect_to_database('pymysql', mysql_database_name,
                           mysql_username, mysql_password, mysql_host)
    # Sync products with odoo IDS
    sync_ibas_products(db, client)

    # Sync Vendors with Odoo IDS
    sync_ibas_vendors(db, client)

    sync_purchase_orders(db, client)

    #

    print("Done.")


if __name__ == "__main__":
    minimal_task()
