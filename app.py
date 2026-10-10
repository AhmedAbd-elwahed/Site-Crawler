import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urlparse, urljoin
import re

# ضبط إعدادات الصفحة
st.set_page_config(page_title="زاحف المواقع وكاشف الصفحات المعزولة", layout="wide")

st.title("🕷️ أداة زاحف موقع المنافس وكاشف الصفحات المعزولة (Site Crawler & Orphan Finder)")
st.write("أدخل رابط المنافس لاستخراج جميع صفحاته، تصنيفها تلقائياً، وكشف الصفحات المعزولة (Orphan Pages) غير المربوطة بلينكات داخلية.")

# خانة إدخال الرابط
target_url = st.text_input("رابط موقع المنافس:", placeholder="https://example.com")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# دالة جلب خرائط الموقع
def get_sitemap_urls(base_url):
    sitemap_candidates = [
        f"{base_url}/sitemap.xml",
        f"{base_url}/sitemap_index.xml",
        f"{base_url}/wp-sitemap.xml"
    ]
    
    found_urls = set()
    
    for s_url in sitemap_candidates:
        try:
            res = requests.get(s_url, headers=headers, timeout=8)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'xml') if 'xml' in res.text[:100] or 'xml' in res.headers.get('Content-Type', '') else BeautifulSoup(res.text, 'html.parser')
                locs = soup.find_all('loc')
                
                for loc in locs:
                    loc_text = loc.get_text().strip()
                    # لو الخريطة شجرة خرائط فرعية (Sitemap Index)
                    if loc_text.endswith('.xml') and loc_text != s_url:
                        try:
                            sub_res = requests.get(loc_text, headers=headers, timeout=8)
                            if sub_res.status_code == 200:
                                sub_soup = BeautifulSoup(sub_res.text, 'html.parser')
                                for sub_loc in sub_soup.find_all('loc'):
                                    found_urls.add(sub_loc.get_text().strip())
                        except:
                            pass
                    else:
                        found_urls.add(loc_text)
                if found_urls:
                    break
        except:
            pass
            
    return found_urls

# دالة الزحف الداخلي للروابط
def get_internal_links(base_url):
    internal_links = set()
    domain = urlparse(base_url).netloc
    
    try:
        res = requests.get(base_url, headers=headers, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href'].strip()
                full_url = urljoin(base_url, href)
                parsed_href = urlparse(full_url)
                
                # التأكد من أن الرابط ينتمي لنفس الدومين وليس ملفاً أو رابطاً خارجياً
                if parsed_href.netloc == domain and not any(full_url.endswith(ext) for ext in ['.jpg', '.png', '.pdf', '.zip', '.css', '.js']):
                    clean_url = full_url.split('#')[0].rstrip('/')
                    if clean_url:
                        internal_links.add(clean_url)
    except:
        pass
        
    return internal_links

# دالة تصنيف نوع الصفحة بناء على الرابط
def categorize_url(url):
    url_lower = url.lower()
    if '/product-category/' in url_lower or '/category/' in url_lower or '/categories/' in url_lower:
        return 'قسم / تصنيف (Category)'
    elif '/product/' in url_lower or '/item/' in url_lower or '/shop/' in url_lower:
        return 'منتج (Product)'
    elif '/blog/' in url_lower or '/news/' in url_lower or '/article/' in url_lower or '/post/' in url_lower:
        return 'مقال / مدونة (Blog)'
    elif url_lower.endswith('.xml'):
        return 'خريطة موقع (Sitemap)'
    else:
        return 'صفحة عامة / أخرى'

# دالة جلب عنوان الصفحة (Title)
def get_page_title(url):
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            if soup.title and soup.title.string:
                return soup.title.string.strip()
    except:
        pass
    return "تعذر الجلب"

# زر بدء الزحف والتحليل
if st.button("بدء الزحف وكشف الصفحات 🚀"):
    if not target_url:
        st.warning("يرجى إدخال رابط الموقع أولاً.")
    else:
        if not target_url.startswith(('http://', 'https://')):
            target_url = 'https://' + target_url

        target_url = target_url.rstrip('/')
        
        st.info("🔍 جاري جرف خريطة الموقع والروابط الداخلية...")
        
        sitemap_urls = get_sitemap_urls(target_url)
        internal_urls = get_internal_links(target_url)
        
        all_unique_urls = list(set(sitemap_urls).union(set(internal_urls)))
        
        if not all_unique_urls:
            st.error("لم يتم العثور على أي روابط في الموقع، قد يكون هناك حظر حماية على السيرفر.")
        else:
            data = []
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            total_items = len(all_unique_urls)
            
            for index, url in enumerate(all_unique_urls):
                status_text.text(f"جاري معالجة الصفحة {index + 1} من {total_items}...")
                progress_bar.progress((index + 1) / total_items)
                
                in_sitemap = url in sitemap_urls
                in_internal = url in internal_urls
                
                # كشف حالة الربط (هل هي معزولة؟)
                if in_sitemap and not in_internal:
                    link_status = "⚠️ صفحة معزولة (Orphan Page)"
                elif in_sitemap and in_internal:
                    link_status = "✅ مربوطة وسليمة"
                else:
                    link_status = "🔗 مكتشفة من الزحف الداخلي فقط"
                    
                category = categorize_url(url)
                page_title = get_page_title(url)
                
                data.append({
                    'رابط الصفحة (URL)': url,
                    'عنوان الصفحة (Page Title)': page_title,
                    'نوع الصفحة': category,
                    'حالة الربط والربط الداخلي': link_status,
                    'موجودة بالـ Sitemap': "نعم" if in_sitemap else "لا",
                    'مربوطة بالرئيسية': "نعم" if in_internal else "لا"
                })
                
            progress_bar.empty()
            status_text.empty()
            
            df = pd.DataFrame(data)
            
            st.success("تم الزحف وتحليل جميع الصفحات بنجاح!")
            
            # عرض كروت ملخص الإحصائيات
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("إجمالي الصفحات المكتشفة", len(df))
            col2.metric("عدد الأقسام", len(df[df['نوع الصفحة'] == 'قسم / تصنيف (Category)']))
            col3.metric("عدد المنتجات", len(df[df['نوع الصفحة'] == 'منتج (Product)']))
            col4.metric("الصفحات المعزولة (Orphan)", len(df[df['حالة الربط والربط الداخلي'] == '⚠️ صفحة معزولة (Orphan Page)']))
            
            st.markdown("---")
            
            # فلتر لعرض النتائج
            filter_option = st.selectbox(
                "تصفية النتائج المعروضة:",
                ["جميع الصفحات", "الصفحات المعزولة فقط (Orphan Pages)", "الأقسام فقط", "المنتجات فقط"]
            )
            
            filtered_df = df.copy()
            if filter_option == "الصفحات المعزولة فقط (Orphan Pages)":
                filtered_df = df[df['حالة الربط والربط الداخلي'] == '⚠️ صفحة معزولة (Orphan Page)']
            elif filter_option == "الأقسام فقط":
                filtered_df = df[df['نوع الصفحة'] == 'قسم / تصنيف (Category)']
            elif filter_option == "المنتجات فقط":
                filtered_df = df[df['نوع الصفحة'] == 'منتج (Product)']
                
            st.dataframe(filtered_df, use_container_width=True)
            
            st.markdown("---")
            
            # تجهيز البيانات للنسخ المباشر لـ Google Sheets
            tsv_data = filtered_df.to_csv(index=False, sep='\t')
            
            st.subheader("📋 نسخ البيانات المصفاة للقطها بداخل Google Sheets")
            st.caption("اضغط على أيقونة النسخ 📋 في الزاوية العلوية للمربع، ثم اعمل Paste بداخل الشيت مباشرة:")
            st.code(tsv_data, language='text')
            
            # زر تنزيل CSV
            csv_data = filtered_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="⬇️ تحميل الجدول المصفى كملف CSV",
                data=csv_data,
                file_name="site_crawler_results.csv",
                mime="text/csv"
            )
