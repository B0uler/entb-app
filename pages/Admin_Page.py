import streamlit as st
import sqlite3
import os
import sys

# --- Импорты ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from code.auth import check_password, add_user
from code.db_helpers import (
    get_db_connection, # Важный импорт, который был пропущен
    get_table_names, get_records, global_search_records, 
    get_record_by_id, update_record, delete_record, get_all_tags, 
    add_new_tag, update_tag, delete_tag, get_image_as_base64
)
from code.i18n import t, language_selector

# --- Настройка страницы и CSS ---
st.set_page_config(page_title=t('sidebar_admin'), page_icon="⚙️", layout="wide")
st.markdown("""
<style>
.img-container-admin, .edit-img-container {
    display: flex; justify-content: center; align-items: center; 
    background-color: var(--secondary-background-color); border-radius: 0.5rem;
}
.img-container-admin { width: 150px; height: 100px; }
.edit-img-container { width: 200px; height: 150px; margin-bottom: 1rem; }
.img-container-admin img, .edit-img-container img {
    max-width: 100%; max-height: 100%; object-fit: contain;
}
</style>
""", unsafe_allow_html=True)

# --- 1. Константы ---
RECORDS_PER_PAGE = 30

# --- 2. UI Функции ---
def login_form():
    st.title(t('login_form_title'))
    with st.form("Login"):
        username, password = st.text_input(t('login_form_username')), st.text_input(t('login_form_password'), type="password")
        if st.form_submit_button(t('login_form_button')):
            is_valid, user_name, is_admin = check_password(username, password)
            if is_valid:
                st.session_state.update({'authenticated': True, 'username': username, 'name': user_name, 'is_admin': is_admin}); st.rerun()
            else: st.error(t('login_form_error'))

def register_form():
    st.header(t('register_form_title'))
    with st.form("Register", clear_on_submit=True):
        new_username, new_password = st.text_input(t('register_form_username')), st.text_input(t('register_form_new_password'), type="password")
        confirm_password = st.text_input(t('register_form_confirm_password')); new_name = st.text_input(t('register_form_display_name'))
        is_admin_checkbox = st.checkbox(t('register_form_is_admin'))
        if st.form_submit_button(t('register_button')):
            if new_password and new_password == confirm_password:
                add_user(new_username, new_password, new_name, 1 if is_admin_checkbox else 0); st.success(t('register_success'))
            else: st.error(t('register_error_password_mismatch'))

# --- 3. Боковая панель ---
language_selector()
if st.session_state.get('authenticated'):
    st.sidebar.success(f"{t('logged_in_as_sidebar')} **{st.session_state.name}**")

# --- 4. Основная логика страницы ---
st.title(t('admin_panel_title'))

if not st.session_state.get('authenticated'):
    login_form()
elif not st.session_state.get('is_admin'):
    st.error(t('permission_denied'))
else: 
    tab1, tab2, tab3 = st.tabs([t('tab_records'), t('tab_tags'), t('tab_register')])
    with tab1:
        editing_info = st.session_state.get('editing_record_info')
        if editing_info:
            record = get_record_by_id(editing_info['table'], editing_info['rowid'])
            if record:
                with st.form(key=f"edit_form_{record['rowid']}"):
                    st.subheader(f"{t('edit_form_title')} `{record['Путь']}`")
                    if record['Фото'] and os.path.exists(record['Фото']):
                        b64_image = get_image_as_base64(record['Фото'])
                        if b64_image: st.markdown(f'<div class="edit-img-container"><img src="data:image/png;base64,{b64_image}"></div>', unsafe_allow_html=True)
                    comment = st.text_area(t('edit_form_comment'), record['Комментарий'] or "")
                    all_tags_suggestions = get_all_tags(); current_tags = record['tags'].split(',') if record['tags'] else []
                    current_tags = [tag.strip() for tag in current_tags if tag.strip()]
                    selected_tags = st.multiselect(t('edit_form_tags'), options=all_tags_suggestions, default=current_tags)
                    uploaded_file = st.file_uploader(t('edit_form_photo'))
                    save, cancel = st.columns(2)
                    if save.form_submit_button(t('save_button')):
                        tags_to_save = ",".join(selected_tags); photo_path = record['Фото']
                        if uploaded_file:
                            table_name = editing_info['table']; table_img_dir = os.path.join('img', table_name)
                            os.makedirs(table_img_dir, exist_ok=True)
                            filename = f"{record['rowid']}_{uploaded_file.name}".replace('\\','_').replace('/','_'); photo_path = os.path.join(table_img_dir, filename)
                            with open(photo_path, "wb") as f: f.write(uploaded_file.getbuffer())
                        update_record(editing_info['table'], record['rowid'], comment, tags_to_save, photo_path)
                        st.session_state.editing_record_info = None; st.rerun()
                    if cancel.form_submit_button(t('cancel_button')):
                        st.session_state.editing_record_info = None; st.rerun()
        else:
            st.header(t('tab_records'))
            c1, c2 = st.columns([1, 2]); table_options = [t('all_tables')] + get_table_names()
            sel_table_idx = table_options.index(st.session_state.get('selected_table', t('all_tables'))) if st.session_state.get('selected_table', t('all_tables')) in table_options else 0
            selected_table = c1.selectbox(t('table_header_table'), table_options, index=sel_table_idx)
            search_query = c2.text_input(t('search_by_path'), st.session_state.get('search_query', ''))
            if selected_table != st.session_state.get('selected_table') or search_query != st.session_state.get('search_query'):
                st.session_state.update({'selected_table': selected_table, 'search_query': search_query, 'current_page': 1}); st.rerun()
            all_records = []
            if selected_table == t('all_tables'):
                if search_query: all_records = global_search_records(search_query)
                else: st.info(t('enter_query_global_search'))
            else: all_records = get_records(selected_table, search_query)
            if all_records:
                total_records = len(all_records); total_pages = max(1, (total_records + RECORDS_PER_PAGE - 1) // RECORDS_PER_PAGE); current_page = st.session_state.get('current_page', 1); current_page = min(current_page, total_pages); st.session_state.current_page = current_page
                start_idx, end_idx = (current_page - 1) * RECORDS_PER_PAGE, current_page * RECORDS_PER_PAGE
                records_to_display = all_records[start_idx:end_idx]
                st.write(f"{t('records_found')} {total_records}")
                cols = st.columns([2, 5, 2, 3, 2, 1, 1]); cols[0].subheader(t('table_header_table')); cols[1].subheader(t('table_header_path')); cols[2].subheader(t('table_header_subfile')); cols[3].subheader(t('table_header_comment')); cols[4].subheader(t('table_header_photo'))
                deleting_info = st.session_state.get('deleting_record_info')
                for r in records_to_display:
                    row_cols = st.columns([2, 5, 2, 3, 2, 1, 1]); row_cols[0].write(r['source_table']); row_cols[1].markdown(f"`{r['Путь']}`"); row_cols[2].write(r['Подфайл'] or ''); row_cols[3].write(r['Комментарий'] or '')
                    if r['Фото'] and os.path.exists(r['Фото']):
                        b64_image = get_image_as_base64(r['Фото'])
                        if b64_image: row_cols[4].markdown(f'<div class="img-container-admin"><img src="data:image/png;base64,{b64_image}"></div>', unsafe_allow_html=True)
                    else: row_cols[4].markdown('<div class="img-container-admin">---</div>', unsafe_allow_html=True)
                    if deleting_info and deleting_info['rowid'] == r['rowid']:
                        row_cols[5].write(t('are_you_sure')); 
                        if row_cols[6].button(t('confirm_delete_button'), key=f"del_confirm_{r['rowid']}"):
                            delete_record(deleting_info['table'], deleting_info['rowid']); st.session_state.deleting_record_info = None; st.rerun()
                    else:
                        if row_cols[5].button(t('edit_button'), key=f"edit_{r['rowid']}"):
                            st.session_state.editing_record_info = {'table': r['source_table'], 'rowid': r['rowid']}; st.rerun()
                        if row_cols[6].button(t('delete_button'), key=f"del_{r['rowid']}"):
                            st.session_state.deleting_record_info = {'table': r['source_table'], 'rowid': r['rowid']}; st.rerun()
                st.divider()
                p1,p2,p3 = st.columns([3,1,3]);
                if p1.button(t('pagination_prev'), disabled=current_page<=1): st.session_state.current_page-=1; st.rerun()
                p2.write(f"{t('pagination_page')} {current_page} {t('pagination_of')} {total_pages}")
                if p3.button(t('pagination_next'), disabled=current_page>=total_pages): st.session_state.current_page+=1; st.rerun()
    with tab2:
        st.header(t('tag_management_title'))
        with st.form("add_tag_form", clear_on_submit=True):
            st.subheader(t('create_new_tag_subheader')); new_tag_name = st.text_input(t('tag_name_label')); new_tag_desc = st.text_area(t('tag_desc_label'))
            if st.form_submit_button(t('create_button')):
                if new_tag_name:
                    try: add_new_tag(new_tag_name, new_tag_desc); st.success(t('tag_create_success').format(tag_name=new_tag_name))
                    except sqlite3.IntegrityError: st.error(t('tag_create_error_exists').format(tag_name=new_tag_name))
                else: st.warning(t('tag_create_error_empty'))
        st.divider()
        tag_records = [];
        with get_db_connection() as conn: tag_records = conn.cursor().execute("SELECT id, name, description FROM tags ORDER BY name").fetchall()
        st.subheader(f"{t('existing_tags_subheader')} ({len(tag_records)})")
        for tag in tag_records:
            if st.session_state.get('editing_tag_id') == tag['id']:
                with st.form(key=f"edit_tag_{tag['id']}"):
                    edited_name = st.text_input(t('tag_name_label'), value=tag['name']); edited_desc = st.text_area(t('tag_desc_label'), value=tag['description'] or "")
                    c1, c2 = st.columns(2)
                    if c1.form_submit_button(t('save_button')): update_tag(tag['id'], edited_name, edited_desc); st.session_state.editing_tag_id = None; st.rerun()
                    if c2.form_submit_button(t('cancel_button')): st.session_state.editing_tag_id = None; st.rerun()
            else:
                c1, c2, c3, c4 = st.columns([2, 4, 1, 1]); c1.write(f"**{tag['name']}**"); c2.write(tag['description'] or "---")
                if c3.button(t('edit_button'), key=f"edit_tag_{tag['id']}"): st.session_state.editing_tag_id = tag['id']; st.rerun()
                if st.session_state.get('deleting_tag_id') == tag['id']:
                    if c4.button(t('confirm_delete_button'), key=f"del_confirm_tag_{tag['id']}"): delete_tag(tag['id']); st.session_state.deleting_tag_id = None; st.rerun()
                else:
                    if c4.button(t('delete_button'), key=f"del_tag_{tag['id']}"): st.session_state.deleting_tag_id = {'table': 'tags', 'id': tag['id']}; st.rerun()
            st.divider()
    with tab3:
        register_form()
