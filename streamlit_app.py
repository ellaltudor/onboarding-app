import streamlit as st

st.title("🎈 My new app")
st.write(
    "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
)

import streamlit as st
import pandas as pd
import sqlalchemy as sa

# Database connection setup
engine = sa.create_engine('your_database_connection_string')

# Function to get data based on user input
def get_grades(category_id, retailer_id):
    query = f"""
    WITH SummedSales AS (
        SELECT p.retailerid, p.subcategoryid, s.retailersku, SUM(s.estimatesales) AS total_sales
        FROM atlasproductsales s
        JOIN retailerproducts p
        ON s.retailersku = p.retailersku AND s.retailerid = p.retailerid
        WHERE s.weekid >= DATEPART(WEEK, DATEADD(WEEK, -52, GETDATE()))
        GROUP BY p.retailerid, p.subcategoryid, s.retailersku
    ),
    RankedSKUs AS (
        SELECT ss.retailerid, ss.subcategoryid, ss.retailersku, ss.total_sales,
               ROW_NUMBER() OVER (PARTITION BY ss.retailerid, ss.subcategoryid ORDER BY ss.total_sales DESC) AS rank
        FROM SummedSales ss
    ),
    TopSKUs AS (
        SELECT rs.retailerid, rs.subcategoryid, rs.retailersku
        FROM RankedSKUs rs
        WHERE rs.rank <= 1000
    ),
    TotalSKUs AS (
        SELECT retailerid, subcategoryid, COUNT(*) AS TotalSKUCount
        FROM SummedSales
        GROUP BY retailerid, subcategoryid
    ),
    CountInAssignedCategories AS (
        SELECT t.retailerid, t.subcategoryid, COUNT(*) AS Count
        FROM TopSKUs t
        JOIN assignedcategories a
        ON t.retailersku = a.retailersku AND t.retailerid = a.retailerid
        WHERE t.retailerid = {retailer_id}
        GROUP BY t.retailerid, t.subcategoryid
    ),
    AggregatedResults AS (
        SELECT ts.retailerid, ts.subcategoryid,
               rp.subcategoryname, rp.categoryname, rp.categoryid,
               COALESCE(ca.Count, 0) AS CountInAssignedCategories,
               CASE
                   WHEN ts.TotalSKUCount <= 1000 THEN 'A'
                   WHEN 100.0 * COALESCE(ca.Count, 0) / 1000 >= 100 THEN 'A'
                   WHEN 100.0 * COALESCE(ca.Count, 0) / 1000 >= 50 THEN 'B'
                   WHEN 100.0 * COALESCE(ca.Count, 0) / 1000 >= 10 THEN 'C'
                   ELSE 'D'
               END AS Grade
        FROM TotalSKUs ts
        LEFT JOIN CountInAssignedCategories ca
        ON ts.retailerid = ca.retailerid AND ts.subcategoryid = ca.subcategoryid
        JOIN retailerproducts rp
        ON ts.retailerid = rp.retailerid AND ts.subcategoryid = rp.subcategoryid
        WHERE ts.retailerid = {retailer_id} AND rp.categoryid = {category_id}
    )
    SELECT DISTINCT categoryid, categoryname, subcategoryid, subcategoryname, 
                    CountInAssignedCategories, Grade
    FROM AggregatedResults
    ORDER BY categoryid, subcategoryid;
    """

    df = pd.read_sql(query, engine)
    return df

# Streamlit app layout
st.title('Category and Subcategory Grading')

# Input fields
category_id = st.text_input('Enter Category ID:')
retailer_id = st.text_input('Enter Retailer ID:')

if st.button('Get Grades'):
    if category_id and retailer_id:
        df = get_grades(category_id, retailer_id)
        if not df.empty:
            st.write('### Grades and To-Do List')
            st.dataframe(df)
            
            st.write('### To-Do List for Grades Below C:')
            df_below_c = df[df['Grade'] == 'D']
            st.dataframe(df_below_c)
        else:
            st.write('No data found for the given Category ID and Retailer ID.')
    else:
        st.write('Please enter both Category ID and Retailer ID.')
