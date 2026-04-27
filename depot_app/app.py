import streamlit as st
from supabase import create_client
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import threading
import streamlit.components.v1 as components
st.set_page_config(layout="wide")
if "filtered_orders" not in st.session_state:
    st.session_state.filtered_orders = None

if "page" not in st.session_state:
    st.session_state.page = 1
if "refresh" in st.session_state and st.session_state["refresh"]:
    st.session_state["refresh"] = False
    st.rerun()

@st.cache_data(show_spinner=False)
def get_route_cached(d_lat, d_long, dl_lat, dl_long):
    return get_dynamic_routes(d_lat, d_long, dl_lat, dl_long)


st.set_page_config(page_title="Depot App", layout="wide")
GOOGLE_API_KEY = "AIzaSyD6kKoeqpSS76MSIg9kREgPsw2j_v1LmDo"

def get_dynamic_routes(depot_lat, depot_long, dealer_lat, dealer_long):
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": "routes.distanceMeters,routes.duration"
    }

    body = {
        "origin": {
            "location": {
                "latLng": {
                    "latitude": depot_lat,
                    "longitude": depot_long
                }
            }
        },
        "destination": {
            "location": {
                "latLng": {
                    "latitude": dealer_lat,
                    "longitude": dealer_long
                }
            }
        },
        "travelMode": "DRIVE",
        "computeAlternativeRoutes": True
    }

    response = requests.post(url, json=body, headers=headers)
    data = response.json()

  

    route_data = []

    if "routes" in data:
        for i, route in enumerate(data["routes"]):
            distance_km = round(route["distanceMeters"] / 1000, 1)

            duration_text = route["duration"].replace("s", "")
            eta_min = round(int(duration_text) / 60)

            route_data.append({
                "name": f"Route {i+1}",
                "distance": distance_km,
                "eta": eta_min
            })

    return route_data
import requests

def get_weather_forecast(lat, lon):
    api_key = "4ec57cecc30c823f1b3a8a602812bd28"

    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&units=metric&appid={api_key}"

    res = requests.get(url)

    if res.status_code == 200:
        data = res.json()

        hourly = []

        for item in data["list"][:8]:
            time_raw = item["dt_txt"].split(" ")[1][:5]

            # convert to AM/PM
            hour = int(time_raw[:2])
            suffix = "AM" if hour < 12 else "PM"
            hour = hour % 12 or 12
            time = f"{hour} {suffix}"

            temp = round(item["main"]["temp"])
            weather = item["weather"][0]["main"]
            rain_prob = int(item.get("pop", 0) * 100)

            hourly.append({
                "time": time,
                "temp": temp,
                "weather": weather,
                "rain": rain_prob
            })

        return hourly

    return []

# ---------------- SUPABASE ----------------
url = "https://yewmxtzbygmcaicpmxfz.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inlld214dHpieWdtY2FpY3BteGZ6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQ5NzM5MzgsImV4cCI6MjA5MDU0OTkzOH0.3KzP09-g4ThJg9JuZZ2jbVrCLhCtIDuWkc13lvqAgzg"
supabase = create_client(url, key)
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user" not in st.session_state:
    st.session_state.user = None


# ---------------- LOGIN PAGE ----------------
def login_page():
    st.markdown("""
    <style>
    .login-title {
        font-size: 42px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 25px;
    }

    .stButton > button {
        width: 100%;
        height: 45px;
        border-radius: 10px;
        font-size: 18px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

    left, center, right = st.columns([1, 2, 1])

    with center:
        st.markdown(
            '<div class="login-title">🏭 Depot Login</div>',
            unsafe_allow_html=True
        )

        email = st.text_input("Email ID")
        password = st.text_input("Password", type="password")

        # -------- FETCH DEPOT LIST --------
        depot_data = supabase.table("depot_master") \
            .select("depot_name, depot_code") \
            .execute()

        if depot_data.data:
            depot_options = [
                f"{row['depot_name']} ({row['depot_code']})"
                for row in depot_data.data
            ]
        else:
            st.error("No depot data found")
            st.stop()

        selected_depot = st.selectbox("Select Depot", depot_options)

        depot_code = selected_depot.split("(")[-1].replace(")", "")

        col1, col2 = st.columns(2)

        with col1:
            login_clicked = st.button("LOGIN")

        with col2:
            register_clicked = st.button("NEW REGISTER")

        # -------- LOGIN LOGIC --------
        if login_clicked:
            with st.spinner("Checking login..."):
                user = supabase.table("user_master") \
                    .select("*") \
                    .eq("email", email.strip()) \
                    .execute()

                if user.data:
                    db_user = user.data[0]

                    if (
                        db_user["password"] == password
                        and db_user["role"] == "depot"
                        and db_user["depot_code"] == depot_code
                    ):
                        st.session_state.logged_in = True
                        st.session_state.user = db_user
                        st.success("Login successful")
                        st.rerun()
                    else:
                        st.error(
                            f"Access denied. Assigned depot: {db_user['depot_code']}"
                        )
                else:
                    st.error("User not found")

        # -------- REGISTER BUTTON --------
        if register_clicked:
            st.info("Please contact admin for new access")


# ---------------- MAIN APP ----------------
if not st.session_state.logged_in:
    login_page()
    st.stop()

# ---------------- SESSION SAFETY ----------------
if st.session_state.logged_in and st.session_state.user is None:
    st.session_state.logged_in = False
    st.rerun()

# ---------------- DASHBOARD ----------------
if st.session_state.logged_in and st.session_state.user is not None:
    user = st.session_state.user
    depot_code = user["depot_code"]
    

    st.title(f"🏭 Depot Hub - {depot_code}")
    st.success(f"Welcome {user['email']}")

    menu = st.sidebar.radio(
        "Menu",
        ["Dashboard","Stock View", "Order list", "Pending Orders", "Stock Entry","Damage Stock", "Logout"]
    )

    # -------- KPI DASHBOARD --------
    if menu == "Dashboard":
       stock_chart_data = supabase.table("stock_summary_view") \
         .select("product_name,total_bags") \
         .eq("depot_code", depot_code) \
         .execute()

       stock_df = pd.DataFrame(stock_chart_data.data)
       if stock_df.empty:
            st.warning("⚠️ No stock data available for this depot")
            stock_df = pd.DataFrame(columns=["product_name", "total_bags"])

       st.subheader("🏭 Overall Depot Performance")

# ---------------- STOCK DATA ----------------
       stock_details = supabase.table("depot_stock") \
         .select("product_name, number_of_bags, available_stock") \
         .eq("depot_code", depot_code) \
         .execute()

       stock_data = stock_details.data if stock_details.data else []

       total_stock_items = len(stock_data)

       total_bags_available = sum(
          int(item["number_of_bags"])
          for item in stock_data
       ) if stock_data else 0

       used_mt = sum(
         float(item["available_stock"])
         for item in stock_data
       ) if stock_data else 0

# ---------------- DEPOT CAPACITY ----------------
       depot_info = supabase.table("depot_master") \
        .select("capacity_mt") \
        .eq("depot_code", depot_code) \
        .execute()

       capacity_mt = float(depot_info.data[0]["capacity_mt"])

       fill_rate = (
         (used_mt / capacity_mt) * 100
         if capacity_mt > 0 else 0
       )

# ---------------- ORDER DATA ----------------
       overall_orders = supabase.table("dealer_orders") \
          .select("bags, order_date") \
          .eq("assigned_depot", depot_code) \
          .execute()

       overall_orders_data = overall_orders.data if overall_orders.data else []

       total_orders = len(overall_orders_data)

       total_bags_sold = sum(
         int(order["bags"])
         for order in overall_orders_data
       ) if overall_orders_data else 0
       
# ---------------- AVG SELLING RATE ----------------
       if overall_orders_data:
          order_dates = [
             pd.to_datetime(order["order_date"]).date()
             for order in overall_orders_data
          ]
          active_days = (max(order_dates) - min(order_dates)).days + 1
       else:
          active_days = 1

       avg_selling_rate = total_bags_sold / active_days

# ---------------- AVG ORDER SIZE ----------------
       avg_order_size = (
          total_bags_sold / total_orders
          if total_orders > 0 else 0
       )

# ---------------- LOW STOCK ----------------
       LOW_STOCK_THRESHOLD = 300

       low_stock_skus = len(
           stock_df[stock_df["total_bags"] < LOW_STOCK_THRESHOLD]
       )
       # ---------------- OVERALL ORDERS ----------------
       overall_orders = supabase.table("dealer_orders") \
              .select("bags, order_date, product_name") \
              .eq("assigned_depot", depot_code) \
              .execute()

       overall_orders_data = overall_orders.data if overall_orders.data else []

       total_orders = len(overall_orders_data)

       total_bags_sold = sum(
             int(order["bags"])
             for order in overall_orders_data
        ) if overall_orders_data else 0
       # ---------------- Dead stocks ----------------
       from datetime import datetime, timedelta

       cutoff_date = datetime.today().date() - timedelta(days=30)

       recent_orders = [
         order for order in overall_orders_data
         if pd.to_datetime(order["order_date"]).date() >= cutoff_date
       ]

       recent_products = set(
          order["product_name"]
          for order in recent_orders
       )

       dead_stock_skus = len(
         stock_df[
           ~stock_df["product_name"].isin(recent_products)
         ]
       )


       # ---------------- KPI CARDS ----------------
       k1, k2, k3, k4 = st.columns(4)

# common style
       def kpi_card(title, value, subtext=""):
           return f"""
          <div style="
              padding:15px;
              border-radius:12px;
              background-color:#f5f7fa;
              text-align:center;
              box-shadow:0 2px 6px rgba(0,0,0,0.1);
              height:120px;              /* ✅ FIXED HEIGHT */
              display:flex;
              flex-direction:column;
             justify-content:center;
          ">
             <div style="font-size:15px;">{title}</div>
             <div style="font-size:22px;font-weight:bold;">{value}</div>
             <div style="font-size:14px;color:gray;">{subtext}</div>
         </div>
         """

# k1 - Avg Selling Rate
       with k1:
            st.markdown(
                kpi_card("📈 Avg Selling Rate", f"{avg_selling_rate:.1f}/day"),
                unsafe_allow_html=True
            )

# k2 - Dead Stock
       with k2:
           st.markdown(
              kpi_card("📦 Avg Order Size", f"{avg_order_size:.1f}", "bags/order"),
              unsafe_allow_html=True
          )
          

# k3 - Avg Order Size
       with k3:
            st.markdown(
              kpi_card("📉 Dead Stock SKUs", dead_stock_skus, "no movement"),
              unsafe_allow_html=True
           )
          

# ---- FETCH DAMAGED STOCK
       damaged_data = supabase.table("depot_stock") \
            .select("damaged_bags") \
            .eq("depot_code", depot_code) \
            .execute()

       damaged_list = damaged_data.data if damaged_data.data else []

       total_damaged_bags = sum(
            int(item["damaged_bags"] or 0)
            for item in damaged_list
        )

        # 🔹 KPI CARD
       with k4:
            st.markdown(
                kpi_card("⚠️ Total Damaged Bags", total_damaged_bags, "needs attention"),
                unsafe_allow_html=True
            )
       
       # ---------------- PRODUCT STOCK CHART ----------------
       
       
       st.subheader("📦 Product-wise Stock Chart")

       

       fig = px.bar(
           stock_df,
           x="product_name",
           y="total_bags",
           text="total_bags",
           title="Product-wise Available Stock"
       )

       colors = []

       for bags in stock_df["total_bags"]:
           if bags > 400:
             colors.append("green")
           elif bags > 200:
             colors.append("orange")
           else:
             colors.append("red")

       fig.update_traces(marker_color=colors)

       fig.update_layout(
           title="📦 Product-wise Available Stock",
           height=500,
           xaxis_title="Products",
           yaxis_title="Number of Bags",
           xaxis_tickangle=-20,
           showlegend=False
       )

       st.plotly_chart(fig, use_container_width=True)
       low_stock_products = len(
           stock_df[stock_df["total_bags"] < LOW_STOCK_THRESHOLD]
       )
       orders_data = supabase.table("dealer_orders") \
          .select("product_name, bags, order_date") \
         .eq("assigned_depot", depot_code) \
         .execute()

       orders_list = orders_data.data if orders_data.data else []
       st.subheader("⏳ Product-wise Days to Empty")

       stock_df = pd.DataFrame(stock_data)

       if stock_df.empty:
           stock_df = pd.DataFrame(columns=["product_name", "number_of_bags"])

       if "product_name" in stock_df.columns:
           grouped_stock = stock_df.groupby("product_name", as_index=False).agg({
              "number_of_bags": "sum"
           })
       else:
          grouped_stock = pd.DataFrame(columns=["product_name", "number_of_bags"])
       days_empty_rows = []

       for _, row in grouped_stock.iterrows():
            product_name = row["product_name"]
            current_stock = max(int(row["number_of_bags"]), 0)

            product_sales = sum(
               int(order["bags"])
               for order in orders_list
               if order["product_name"] == product_name
            )

            avg_daily_sales = (
               round(product_sales / active_days, 1)
               if active_days > 0 else 0
            )

            days_to_empty = (
               round(current_stock / avg_daily_sales, 1)
               if avg_daily_sales > 0 else "No sales"
            )

            days_empty_rows.append({
               "Product": product_name,
               "Current Stock": current_stock,
               "Avg Daily Sales": avg_daily_sales,
               "Days to Empty": days_to_empty
            })

       days_empty_df = pd.DataFrame(days_empty_rows)

       st.dataframe(days_empty_df, use_container_width=True)
       

      
       # ---------------- UTILIZATION DATA ----------------
       used_mt = sum(
          float(item["available_stock"])
          for item in stock_details.data
       ) if stock_details.data else 0

       depot_info = supabase.table("depot_master") \
         .select("capacity_mt") \
         .eq("depot_code", depot_code) \
         .execute()

       capacity_mt = float(depot_info.data[0]["capacity_mt"])
       available_mt = capacity_mt - used_mt

       capacity_bags = int(capacity_mt * 20)
       used_bags = sum(
          int(item["number_of_bags"])
          for item in stock_details.data
       ) if stock_details.data else 0
       available_bags = capacity_bags - used_bags

       utilization = (used_mt / capacity_mt) * 100

# ---------------- ACTIVE DAYS ----------------
       if overall_orders_data:
          order_dates = [
             pd.to_datetime(order["order_date"]).date()
             for order in overall_orders_data
          ]
          active_days = (max(order_dates) - min(order_dates)).days + 1
       else:
          active_days = 1
       # ---------------- SPACE UTILIZATION ----------------
       st.subheader("🏭 Depot Space Utilization")

       if utilization < 60:
          st.success(f"🟢 Utilization Healthy: {utilization:.1f}%")
       elif utilization < 85:
         st.warning(f"🟠 Utilization Watch: {utilization:.1f}%")
       else:
         st.error(f"🔴 Utilization Critical: {utilization:.1f}%")

       st.progress(min(max(utilization / 100, 0.0), 1.0))

       col1, col2, col3 = st.columns(3)

       with col1:
         st.markdown(
            f"""
            <div style="padding:15px;border-radius:12px;background-color:#f5f7fa;text-align:center;box-shadow:0 2px 6px rgba(0,0,0,0.1);">
                <div style="font-size:18px;">🏭 Capacity</div>
                <div style="font-size:20px;font-weight:bold;">{capacity_mt:.1f} MT</div>
                <div style="font-size:18px;color:gray;">{capacity_bags} bags</div>
            </div>
            """,
            unsafe_allow_html=True
         )

       with col2:
         st.markdown(
            f"""
            <div style="padding:15px;border-radius:12px;background-color:#f5f7fa;text-align:center;box-shadow:0 2px 6px rgba(0,0,0,0.1);">
                <div style="font-size:18px;">📦 Used</div>
                <div style="font-size:20px;font-weight:bold;">{used_mt:.1f} MT</div>
                <div style="font-size:18px;color:gray;">{used_bags} bags</div>
            </div>
            """,
            unsafe_allow_html=True
         )

       with col3:
         st.markdown(
            f"""
            <div style="padding:15px;border-radius:12px;background-color:#f5f7fa;text-align:center;box-shadow:0 2px 6px rgba(0,0,0,0.1);">
                <div style="font-size:18px;">🟩 Available</div>
                <div style="font-size:20px;font-weight:bold;">{available_mt:.1f} MT</div>
                <div style="font-size:18px;color:gray;">{available_bags} bags</div>
            </div>
            """,
            unsafe_allow_html=True
         )
     

    # -------- stock entry --------
  
    elif menu == "Stock Entry":
       st.markdown(
          "<h1 style='color:red;'>Stock Entry</h1>",
          unsafe_allow_html=True
       )

       grn_no = st.text_input("SAP GRN / Material Document No")
       truck_no = st.text_input("Truck Number")

    # depot dropdown
       st.text_input(
         "Depot Code",
         value=depot_code,
         disabled=True
       )

    # product dropdown
       stock_date = datetime.now().date()
       product_data = supabase.table("product_master").select(
         "product_code, product_name"
       ).execute()
       product_options = {
         row["product_name"]: row
         for row in product_data.data
       }

       selected_product = st.selectbox(
          "Product Name",
          list(product_options.keys())
       )

       product = product_options[selected_product]

       st.success(f"Product Code: {product['product_code']}")

       bag_weight = st.number_input(
           "Bag Weight (kg)",
           min_value=0.0,
           step=1.0,
           value=50.0
       )

       no_of_bags = st.number_input(
         "Number of Bags",
         min_value=0,
         step=1
       )
       import math

       bags_per_stack = 15

       if no_of_bags > 0:

    # 🔹 Get depot capacity grid
          depot = supabase.table("depot_master") \
            .select("total_stacks") \
            .eq("depot_code", depot_code) \
            .execute()

          total_stacks = depot.data[0]["total_stacks"]

          cols = int(math.sqrt(total_stacks))
    
    # 🔹 Get used stacks
         # 🔹 Get occupied locations from depot_stock (CORRECT)
          used = supabase.table("depot_stock") \
            .select("row_no, column_no") \
            .eq("depot_code", depot_code) \
            .execute()

          occupied = {(s["row_no"], s["column_no"]) for s in used.data}

# 🔹 Calculate required stacks
          num_stacks = math.ceil(no_of_bags / bags_per_stack)

# 🔹 Find next available locations
          locations = []

          for r in range(1, 100):
             for c in range(1, cols + 1):
                 if (r, c) not in occupied:
                    locations.append(f"R{r}-C{c}")

                 if len(locations) == num_stacks:
                     break
             if len(locations) == num_stacks:
                   break

# 🔹 Show correct locations
          st.success("📍 Load at Locations: " + ", ".join(locations))
       # ================= AUTO LOCATION =================
      

# 🔹 Get depot capacity (total stacks)
      
       stock_mt = round((bag_weight * no_of_bags) / 1000, 2)

       stock_details = supabase.table("depot_stock") \
           .select("available_stock") \
           .eq("depot_code", depot_code) \
           .execute()

       used_mt = sum(
          float(item["available_stock"])
          for item in stock_details.data
       ) if stock_details.data else 0

       depot_info = supabase.table("depot_master") \
         .select("capacity_mt") \
         .eq("depot_code", depot_code) \
         .execute()

       capacity_mt = float(depot_info.data[0]["capacity_mt"])

       future_used_mt = used_mt + stock_mt
       future_utilization = (future_used_mt / capacity_mt) * 100

       if future_utilization >= 100:
             st.error(f"🚫 Capacity exceeded: {future_utilization:.1f}%")
       else:
           st.success(f"✅ Available capacity after intake: {100 - future_utilization:.1f}%")
       save_disabled = (
           not grn_no.strip()
           or not truck_no.strip()
           or bag_weight <= 0
           or no_of_bags <= 0
           or future_utilization >= 100
       )

       
       if st.button("SAVE GRN", disabled=save_disabled):
          if future_utilization >= 100:
              st.error("🚫 Depot is full. Cannot receive more stock.")
              st.stop()

         

          duplicate_check = supabase.table("depot_stock") \
             .select("id, sap_grn_number") \
             .eq("sap_grn_number", grn_no.strip()) \
             .execute()

       
  

          if duplicate_check.data:
             st.error("🚫 This SAP GRN already exists. Duplicate entry not allowed.")

          

          else:
              remaining = no_of_bags
              # 🔹 Step 1: Fill partially filled stacks
              
              if remaining > 0:

                import math

                depot = supabase.table("depot_master") \
                    .select("total_stacks") \
                    .eq("depot_code", depot_code) \
                    .execute()

                total_stacks = depot.data[0]["total_stacks"]
                cols = int(math.sqrt(total_stacks))

                used = supabase.table("depot_stock") \
                      .select("row_no, column_no") \
                     .eq("depot_code", depot_code) \
                     .execute()

                occupied = {(s["row_no"], s["column_no"]) for s in used.data}
                locations = []

                for r in range(1, 100):
                    for c in range(1, cols + 1):
                       if (r, c) not in occupied:
                          locations.append((r, c))
                
                for (row, col) in locations:
                    if remaining <= 0:
                      break

                    bags = min(15, remaining)
                    remaining -= bags

                    supabase.table("depot_stock").insert({
                        "depot_code": depot_code,
                        "product_code": product["product_code"],
                        "product_name": selected_product,
                        "available_stock": bags * bag_weight / 1000,
                       "number_of_bags": bags,
                       "bag_weight": bag_weight,
                        "row_no": row,
                       "column_no": col,
                       "stock_received_date": str(stock_date),
                       "sap_grn_number": grn_no.strip(),
                       "truck_number": truck_no.strip()
                    }).execute()
       
                st.success("✅ Stock saved successfully")
                if remaining > 0:
                    st.error(f"❌ Not enough empty space! {remaining} bags not stored")
        
            #order list
            
    elif menu == "Order list":
         dealer_list_query = supabase.table("dealer_orders") \
              .select("dealer_id") \
             .eq("assigned_depot", depot_code) \
             .execute()

         dealer_ids = list(set([d["dealer_id"] for d in dealer_list_query.data]))
         dealer_ids.sort()
         st.subheader("📋 Order List")
         st.markdown("### 🔎 Search by Order No")

         order_search = st.text_input("Enter Order No")

         order_btn = st.button("Search Order")

         if order_btn:
           if order_search:
              try:
                result = supabase.table("dealer_orders") \
                  .select("*") \
                  .eq("id", int(order_search)) \
                  .execute()

                if result.data:
                 
                  df = pd.DataFrame(result.data)
                  df = df.rename(columns={"id": "Order No"})
                  st.success("Order Found ✅")
                  st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                  st.warning("No order found")

              except:
                 st.error("Invalid Order Number")
         st.markdown("---")
         st.markdown("### 📅 Search by Date & Dealer")

         col1, col2, col3 = st.columns(3)

         with col1:
            from_date = st.date_input("From Date")

         with col2:
           to_date = st.date_input("To Date")

         with col3:
            dealer_search = st.selectbox("Dealer", ["All"] + dealer_ids)

         filter_btn = st.button("Filter Orders")

         if filter_btn:
            

            query = supabase.table("dealer_orders") \
               .select("*") \
               .eq("assigned_depot", depot_code)

            from datetime import timedelta

            if from_date:
                query = query.gte("order_date", str(from_date))

            if to_date:
                query = query.lt("order_date", str(to_date + timedelta(days=1)))

            result = query.execute()

            if result.data:
               
               df = pd.DataFrame(result.data)
               st.session_state.filtered_orders = df   # 🔥 STORE DATA
               st.session_state.page = 1               # reset page
            else:
                st.session_state.filtered_orders = None
         if st.session_state.get("filtered_orders") is not None:

               df = st.session_state.filtered_orders.copy()

    # ✅ Dealer filter (apply properly)
               if dealer_search != "All":
                  df = df[df["dealer_id"] == dealer_search]

    # ✅ Rename column (always)
               df = df.rename(columns={"id": "Order No"})

    # ---------------- PAGINATION ----------------
               rows_per_page = 10
               total_rows = len(df)

               total_pages = max(1, (total_rows // rows_per_page) + (1 if total_rows % rows_per_page else 0))

    # Session 
               if st.session_state.page > total_pages:
                  st.session_state.page = total_pages
               col1, col2, col3 = st.columns([1,2,1])

               with col1:
                  if st.button("⬅ Previous"):
                     if st.session_state.page > 1:
                        st.session_state.page -= 1

               with col3:
                 if st.button("Next ➡"):
                   if st.session_state.page < total_pages:
                      st.session_state.page += 1
               st.session_state.page = max(1, min(st.session_state.page, total_pages))

               page = st.session_state.page
               if page > total_pages:
                  st.session_state.page = total_pages
                  page = total_pages

               start = (page - 1) * rows_per_page
               end = start + rows_per_page

               df_paginated = df.iloc[start:end]

    # ✅ Show data always
               st.dataframe(df_paginated, use_container_width=True, hide_index=True)

               st.markdown(f"### 📄 Page {page} of {total_pages}")
               st.caption(f"Showing {start+1} to {min(end, total_rows)} of {total_rows} records")


         else:
                st.warning("No orders found")
  
    # -------- PENDING ORDERS --------
    elif menu == "Pending Orders":
        st.subheader("📋 Pending Orders")

        pending = supabase.table("dealer_orders") \
            .select("*") \
            .eq("assigned_depot", depot_code) \
            .in_("status", ["created", "accepted"]) \
            .execute()

        orders = pending.data if pending else []
        dealer_cache = {}
        dealer_master = supabase.table("dealer_master") \
            .select("*") \
            .execute()

        if dealer_master.data:
           for d in dealer_master.data:
              dealer_cache[d["dealer_id"]] = d
      
        # ✅ GET DEPOT LOCATION ONCE (outside loop)
        depot_info = supabase.table("depot_master") \
          .select("latitude, longitude") \
          .eq("depot_code", depot_code) \
          .execute()

        if depot_info.data:
           depot_lat = depot_info.data[0]["latitude"]
           depot_long = depot_info.data[0]["longitude"]
        else:
           st.error("Depot location not found")
        if orders:

        # ================= 🟡 ACCEPT SECTION =================
            st.markdown("## 🟡 Orders to Accept")

            found_accept = False

            for order in orders:
              if order["status"] == "created":
                found_accept = True

                st.markdown("---")

                with st.container():
                    st.markdown(f"### 📦 Order {order['id']}")
                    dealer_id = order["dealer_id"]          # ✅ get from order
                    dealer_data = dealer_cache.get(dealer_id, {})

                    dealer_name = dealer_data["dealer_name"]
                    address = dealer_data["address"]
                    city = dealer_data["city"]

                    st.markdown(f"""
                    **🏪 Dealer:** {dealer_name}  
                    📍 **Address:** {address}, {city}
                    """)
                    st.write(f"Product: {order['product_name']}")
                    st.write(f"Bags: {order['bags']}")
                already_accepted = st.session_state.get(f"accepted_{order['id']}", False)

                if order["status"] == "created" and not already_accepted:

                    if st.button(f"Accept Order {order['id']}", key=f"accept_{order['id']}"):
                       product = supabase.table("product_master") \
                           .select("product_code") \
                           .eq("product_name", order["product_name"]) \
                           .single() \
                           .execute().data

    # 🔥 FIFO PICK PREVIEW (ADD HERE)
                       remaining = order["bags"]

                       stock_rows = supabase.table("depot_stock") \
                            .select("*") \
                            .eq("depot_code", depot_code) \
                            .eq("product_name", order["product_name"]) \
                            .gt("number_of_bags", 0) \
                            .order("stock_received_date") \
                            .order("row_no") \
                            .order("column_no") \
                            .execute()

                       allocations = []

                       for row in stock_rows.data:
                          if remaining <= 0:
                              break

                          available = row["number_of_bags"]
                          take = min(available, remaining)

                          allocations.append({
                              "stock_id": row["id"],
                             "row": row["row_no"],
                             "col": row["column_no"],
                             "bags": take
                          })
                          # 🔥 SAVE TO DB (NEW)
                          supabase.table("order_allocation").insert({
                             "order_id": order["id"],
                             "depot_code": depot_code,
                            "product_code": product["product_code"],
                            "stock_id": row["id"],
                            "row_no": row["row_no"],
                            "column_no": row["column_no"],
                            "bags_taken": take
}).execute()
                          remaining -= take

                       if remaining > 0:
                          st.error("❌ Not enough stock to fulfill order")
                          st.stop()

    # 🔥 SHOW PICK LOCATIONS
                       pick_list = [
                          f"R{a['row']}-C{a['col']} ({a['bags']} bags)"
                          for a in allocations
                       ]

                       st.success("📦 Pick from: " + ", ".join(pick_list))
                       st.session_state[f"alloc_{order['id']}"] = allocations
                       for alloc in allocations:
                           stock_id = alloc["stock_id"]
                           bags_taken = alloc["bags"]

                           stock_data = supabase.table("depot_stock") \
                                .select("number_of_bags, bag_weight") \
                                .eq("id", stock_id) \
                                .execute()

                           current_bags = stock_data.data[0]["number_of_bags"]
                           bag_weight = stock_data.data[0]["bag_weight"]

                           new_bags = current_bags - bags_taken

                           supabase.table("depot_stock").update({
                               "number_of_bags": new_bags,
                               "available_stock": new_bags * bag_weight / 1000
                           }).eq("id", stock_id).execute()
    # 🔥 NOW UPDATE STATUS
                       supabase.table("dealer_orders") \
                          .update({"status": "accepted"}) \
                          .eq("id", order["id"]) \
                          .execute()
                       st.session_state[f"accepted_{order['id']}"] = True


                       st.success("✅ Order Accepted")
                       st.rerun()

            if not found_accept:
               st.info("No orders to accept")

        # ================= 🟢 DISPATCH SECTION =================
            st.markdown("## 🟢 Orders to Dispatch")
            found_dispatch = False

# 🔥 depot fetch (once)
            depot_info = supabase.table("depot_master") \
                .select("latitude, longitude") \
                .eq("depot_code", depot_code) \
                .execute()

            depot_lat = depot_info.data[0]["latitude"]
            depot_long = depot_info.data[0]["longitude"]

            for order in orders:

               if order["status"] != "accepted":
                  continue

               found_dispatch = True
               dealer_id = order["dealer_id"]

    # ================= DEALER DATA =================
               if dealer_id not in dealer_cache:
                  dealer_info = supabase.table("dealer_master") \
                       .select("dealer_name, address, city, latitude, longitude") \
                       .eq("dealer_id", dealer_id) \
                       .execute()

                  dealer_cache[dealer_id] = dealer_info.data[0]

               dealer_data = dealer_cache[dealer_id]

               dealer_lat = dealer_data["latitude"]
               dealer_long = dealer_data["longitude"]

               st.markdown("---")

    # ================= ORDER CARD =================
               st.markdown(f"""
                  <div style="padding:18px;border-radius:14px;background:#f8fafc;
                  box-shadow:0 3px 10px rgba(0,0,0,0.06);border:1px solid #e5e7eb;">
                       <h3>📦 Order {order['id']}</h3>
                       <p><b>Dealer:</b> {dealer_id} - {dealer_data['dealer_name']}</p>
                       <p>📍 {dealer_data['address']}, {dealer_data['city']}</p>
                       <p><b>Product:</b> {order['product_name']}</p>
                       <p><b>Bags:</b> {order['bags']}</p>
                       <p><b>Delivery Type:</b> {order.get('delivery_type', 'FOR')}</p>
                  </div>
                  """, unsafe_allow_html=True)

    # ================= WEATHER =================
               weather_data = get_weather_forecast(dealer_lat, dealer_long)

               def get_icon(weather):
                   return {"Clouds": "☁️", "Rain": "🌧️", "Clear": "🌙"}.get(weather, "🌤️")

               st.markdown("### 🌤 HOURLY WEATHER")

               current_hour = datetime.now().hour
               hours_list = [datetime.strptime(h["time"], "%I %p").hour for h in weather_data]

               start_index = min(
                    range(len(hours_list)),
                    key=lambda i: (hours_list[i] - current_hour) % 24
               )

               filtered_weather = (weather_data[start_index:] + weather_data[:start_index])[:6]

               st.markdown(f"🕒 Current Time: {datetime.now().strftime('%I:%M %p')}")

               cols = st.columns(len(filtered_weather))

               for i, hour in enumerate(filtered_weather):
                 with cols[i]:
                     st.markdown(f"""
                       <div style="text-align:center;padding:12px;border-radius:12px;background:#fff;">
                         <div>{'Now' if i==0 else hour['time']}</div>
                         <div style="font-size:28px">{get_icon(hour['weather'])}</div>
                         <div style="font-weight:bold">{hour['temp']}°</div>
                         <div style="font-size:12px;color:gray">💧 {hour['rain']}%</div>
                       </div>
                      """, unsafe_allow_html=True)

    # ================= WEATHER DECISION =================
               if weather_data:
                 total_rain = sum(h["rain"] for h in weather_data)
                 if total_rain == 0:
                     st.success("✅ Safe to dispatch")
                 else:
                     st.error("🚫 Rain expected – use cover")

    # ================= DELIVERY TYPE =================
               delivery_type = order.get("delivery_type", "FOR")

   
               # ================= ROUTE =================
            
# ✅ Handle both list & dict safely
           
    # ================= MAP =================
              
               if delivery_type == "FOR":
                  embed_url = f"https://www.google.com/maps/embed/v1/directions?key={GOOGLE_API_KEY}&origin={depot_lat},{depot_long}&destination={dealer_lat},{dealer_long}&mode=driving"
                  components.iframe(embed_url, height=400)

    # ================= VEHICLE INPUT =================
               if delivery_type == "FOR":
                    col1, col2 = st.columns(2)
                    with col1:
                      vehicle_no = st.text_input("Vehicle No", key=f"vehicle_{order['id']}")
                    with col2:
                      driver_name = st.text_input("Driver Name", key=f"driver_{order['id']}")
               else:
                 vehicle_no = ""
                 driver_name = ""
                 st.info("⚡ EXD Order - No vehicle required")
               # ================= WEATHER DECISION =================


# ================= STOCK TO DISPATCH =================
               st.markdown("### 📦 Stock to Dispatch")

               allocations_db = supabase.table("order_allocation") \
                   .select("*") \
                   .eq("order_id", order["id"]) \
                    .execute()

               allocations = allocations_db.data if allocations_db.data else []

               if allocations:
                   for a in allocations:
                      st.markdown(
                          f"R{a['row_no']}-C{a['column_no']} → {a['bags_taken']} bags"
                      )
               else:
                   st.warning("⚠️ Accept order first to generate stack allocation")

# ================= VEHICLE INPUT =================

    # ================= STACK INPUT =================
               stack_key = f"stacks_{order['id']}"

               if stack_key not in st.session_state:
                  st.session_state[stack_key] = [{"rows": 0, "cols": 0, "height": 0}]

           

               for i, stack in enumerate(st.session_state[stack_key]):
                  st.markdown(f"### Stack {i+1}")
                  c1, c2, c3 = st.columns(3)

                  stack["rows"] = c1.number_input("Rows", 0, key=f"r_{order['id']}_{i}")
                  stack["cols"] = c2.number_input("Cols", 0, key=f"c_{order['id']}_{i}")
                  stack["height"] = c3.number_input("Height", 0, key=f"h_{order['id']}_{i}")
               if st.button("➕ Add Stack", key=f"add_stack_{order['id']}"):
                  st.session_state[stack_key].append({"rows": 0, "cols": 0, "height": 0})
    # ================= CALCULATE =================
               if st.button("🧮 Calculate", key=f"calc_{order['id']}"):
                   total = sum(s["rows"] * s["cols"] * s["height"] for s in st.session_state[stack_key])
                   st.session_state[f"total_{order['id']}"] = total

               total_bags = st.session_state.get(f"total_{order['id']}", 0)
               st.info(f"📦 Total Bags: {total_bags}")

    # ================= VALIDATION =================
               if total_bags == order["bags"]:
                   st.success("✅ Perfect match")
               elif total_bags > 0:
                  st.error("❌ Mismatch")

    # ================= DISPATCH =================
               if st.button(f"🚚 Dispatch Order {order['id']}", key=f"dispatch_{order['id']}"):

                  if total_bags == 0:
                     st.error("Calculate first")

                  elif total_bags != order["bags"]:
                      st.error("Mismatch")

                  else:
                    if delivery_type == "FOR":
                       if not vehicle_no.strip():
                             st.error("Enter vehicle")
                             st.stop()
                       if not driver_name.strip():
                            st.error("Enter driver")
                            st.stop()
        
        # ✅ Save vehicle stacks
                    supabase.table("order_stacks").delete().eq("order_id", order["id"]).execute()

                    for i, s in enumerate(st.session_state[stack_key]):
                        supabase.table("order_stacks").insert({
                          "order_id": order["id"],
                         "stack_no": i+1,
                         "rows": s["rows"],
                         "columns": s["cols"],
                         "height": s["height"],
                          "total_bags": s["rows"] * s["cols"] * s["height"]
                        }).execute()

        # ✅ Update order
                    supabase.table("dealer_orders").update({
                       "vehicle_no": vehicle_no if delivery_type == "FOR" else None,
                       "driver_name": driver_name if delivery_type == "FOR" else None,
                       "dispatch_time": datetime.now().isoformat(),
                       "assigned_depot": depot_code,
                       "status": "dispatched",
                       "dispatched_bags": total_bags,
                    }).eq("id", order["id"]).execute()

                    st.success("🚚 Order Dispatched Successfully")
                    st.rerun()
                 
                   
                  

# ================= EMPTY =================
            if not found_dispatch:
               st.info("No orders to dispatch")
    
  

    elif menu == "Stock View":

        st.subheader("📦 Depot Stock Layout")

    # 🔹 Fetch stock (INCLUDING product)
        stock_data = supabase.table("depot_stock") \
          .select("row_no, column_no, number_of_bags, product_name, sap_grn_number, created_at") \
          .eq("depot_code", depot_code) \
          .execute()

    
        df = pd.DataFrame(stock_data.data)

        if df.empty:
         st.warning("No stock available")
        else:

        # ---------------- 🔎 FILTER ----------------
          products = df["product_name"].dropna().unique().tolist()
          products.sort()

          selected_product = st.selectbox(
            "🔎 Filter by Product",
            ["All"] + products
          )

          full_df = df.copy()   # 🔴 KEEP ORIGINAL

          if selected_product != "All":
             display_df = df[df["product_name"] == selected_product]
          else:
             display_df = df.copy()

          if df.empty:
            st.warning("No stock for selected product")
            st.stop()
          search_grn = st.text_input("🔍 Enter GRN Number")
          if search_grn:

    # filter only this GRN from full data
            grn_df = full_df[full_df["sap_grn_number"] == search_grn]

            if grn_df.empty:
                st.error("❌ No stock found for this GRN")
            else:
               total_bags = grn_df["number_of_bags"].sum()
               total_locations = len(grn_df)

               products = grn_df["product_name"].dropna().unique().tolist()
               grn_date = grn_df["created_at"].iloc[0]
               grn_date = pd.to_datetime(grn_date).strftime("%d-%m-%Y %H:%M")
               st.markdown(f"""
               <div style='
                  background-color:#f4f6f7;
                  padding:15px;
                  border-radius:10px;
                  margin-top:10px;
              '>
                 <b>📦 GRN Summary</b><br><br>
                 <b>GRN Number:</b> {search_grn} <br>
                 <b>Entry Date:</b> {grn_date} <br>
                 <b>Total Bags:</b> {total_bags} <br>
                 <b>Locations Used:</b> {total_locations} <br>
                 <b>Products:</b> {", ".join(products)}
              </div>
              """, unsafe_allow_html=True)

        # ---------------- GRID SIZE ----------------
          depot_info = supabase.table("depot_master") \
               .select("max_rows, max_columns") \
               .eq("depot_code", depot_code) \
               .single() \
               .execute()

          max_row = depot_info.data["max_rows"]
          max_col = depot_info.data["max_columns"]

        # create empty grid
          grid = [[None for _ in range(max_col)] for _ in range(max_row)]

        # fill grid
          for _, r in display_df.iterrows():
            row = int(r["row_no"]) - 1
            col = int(r["column_no"]) - 1

            if grid[row][col] is None:
                grid[row][col] = {
                   "stock": []
                }

            grid[row][col]["stock"].append({
               "bags": int(r["number_of_bags"]),
               "product": r["product_name"],
               "grn": r["sap_grn_number"]
            })

        # ---------------- DISPLAY GRID ----------------
          for i in range(max_row):
            st.markdown(f"**Row {i+1}**")
            cols = st.columns(max_col)

            for j in range(max_col):

                cell = grid[i][j]

                if cell is None:
                   total_bags = 0
                   grn_bags = 0
                else:
                  stock_list = cell["stock"]

                  total_bags = sum(item["bags"] for item in stock_list)

                  if search_grn:
                    grn_bags = sum(
                        item["bags"] for item in stock_list
                        if item["grn"] == search_grn
                    )
                  else:
                     grn_bags = total_bags

                # 🎨 Color logic
                bags_to_show = grn_bags if search_grn else total_bags

                if search_grn:
                    if grn_bags > 0:
                          color = "#3498db"  # 🔵 highlight GRN match
                    else:
                          color = "#ecf0f1"  # faded
                else:
                     if total_bags == 0:
                           color = "#ff4b4b"
                     elif total_bags < 10:
                          color = "#ffa500"
                     else:
                          color = "#2ecc71"

                

                cols[j].markdown(f"""
                   <div style='
                      background-color:{color};
                      width:70px;
                      height:80px;
                      min-width:70px;
                      min-height:80px;
                      max-width:70px;
                      max-height:80px;
                      border-radius:10px;
                      text-align:center;
                      color:white;
                      display:flex;
                      flex-direction:column;
                      justify-content:center;
                      align-items:center;
                      margin:auto;
                      box-sizing:border-box;
                  '>
                      <div style="font-size:10px;">R{i+1}-C{j+1}</div>
                      <div style="font-size:18px; font-weight:bold;">{bags_to_show}</div>
                 </div>
                """, unsafe_allow_html=True)
    
    elif menu == "Damage Stock":
        st.markdown("### 🚨 Report Damage")

    # ✅ USE EXISTING SESSION (NO LOGIN CHANGE)
        DEPOT_ID = st.session_state.user["depot_code"]

        # -------- FETCH PRODUCTS --------
        products = supabase.table("product_master") \
            .select("product_code, product_name") \
            .execute()

        product_list = products.data
        product_names = [p["product_name"] for p in product_list]

        selected_product = st.selectbox("Select Product", product_names)

        product_id = next(
            p["product_code"] for p in product_list
            if p["product_name"] == selected_product
        )

        # -------- FETCH LOCATIONS --------
        stock_res = supabase.table("depot_stock") \
            .select("row_no, column_no, number_of_bags, damaged_bags") \
            .eq("product_code", product_id) \
            .eq("depot_code", DEPOT_ID) \
            .execute()

        locations = stock_res.data

        valid_locations = [
            loc for loc in locations
            if (loc.get("number_of_bags", 0) or 0) > 0
        ]

        if valid_locations:

            location_options = [
                f"Row {loc['row_no']} - Col {loc['column_no']} (Good: {loc['number_of_bags']})"
                for loc in valid_locations
            ]

            selected_location = st.selectbox("Select Location", location_options)

            row_no = int(selected_location.split()[1])
            column_no = int(selected_location.split()[4])

            selected_loc_data = next(
                loc for loc in valid_locations
                if loc["row_no"] == row_no and loc["column_no"] == column_no
            )

            good_stock = selected_loc_data.get("number_of_bags", 0) or 0
            damaged_stock = selected_loc_data.get("damaged_bags", 0) or 0

            st.info(f"📦 Good: {good_stock} | Damaged: {damaged_stock}")

        else:
            st.warning("⚠️ No available stock locations for this product")
            st.stop()

        qty = st.number_input("Quantity Damaged", min_value=1, max_value=good_stock)

        damage_type = st.selectbox(
            "Damage Type",
            ["Broken", "Moisture damage", "Expired", "Transit damage"]
        )

        remarks = st.text_area("Remarks")

        if st.button("Submit Damage"):

            try:
                supabase.table("damage_requests").insert({
                    "product_id": product_id,
                    "product_name": selected_product,
                    "quantity": qty,
                    "damage_type": damage_type,
                    "remarks": remarks,
                    "status": "pending",
                    "depot_id": DEPOT_ID,
                    "row_no": row_no,
                    "column_no": column_no,
                    "created_by": st.session_state.user["email"]
                }).execute()

                st.success("✅ Damage request sent to admin")
                st.rerun() 
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
            # ---------------- ALWAYS SHOW PENDING LIST ----------------
        st.markdown("### 📋 Pending Requests")

        data = supabase.table("damage_requests") \
            .select("*") \
            .eq("depot_id", DEPOT_ID) \
            .eq("status", "pending") \
            .order("id", desc=True) \
            .execute()

        if not data.data:
            st.info("No pending requests")
        else:
            st.dataframe(data.data, use_container_width=True)
    if menu == "Logout":
    # Clear session
        for key in list(st.session_state.keys()):
            del st.session_state[key]

        st.success("Logged out successfully")

        st.rerun()