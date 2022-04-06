from django.shortcuts import render, redirect, reverse, HttpResponse
from django.contrib import auth
from crm.forms import RegForm, CustomerForm, ConsultRecordForm, EnrollmentForm
from crm import models
from django.utils.safestring import mark_safe
from utils.pagination import Pagination
from django.views import View
from django.db.models import Q
from django.http import QueryDict
import copy
from django.db import transaction
import time
from django.conf import settings
from rbac.server.init_permission import init_permission

from PIL import Image, ImageDraw, ImageFont
import random


def random_color():
    return random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)


def v_code(request):
    img_obj = Image.new('RGB', (250, 35), random_color())
    
    # 在该图片对象上生成一个画笔对象
    draw_obj = ImageDraw.Draw(img_obj)
    
    font_obj = ImageFont.truetype('static/font/kumo.ttf', 28)
    
    temp = []
    for i in range(5):
        l = chr(random.randint(97, 122))  # 小写字母
        b = chr(random.randint(65, 90))  # 大写字母
        n = str(random.randint(0, 9))
        
        t = random.choice([l, b, n])
        temp.append(t)
        
        draw_obj.text((i * 40 + 35, 0), t, fill=random_color(), font=font_obj)
        
    # 加干扰线
    width = 250  # 图片宽度（防止越界）
    height = 35
    for i in range(5):
        x1 = random.randint(0, width)
        x2 = random.randint(0, width)
        y1 = random.randint(0, height)
        y2 = random.randint(0, height)
        draw_obj.line((x1, y1, x2, y2), fill=random_color())
    
    request.session['v_code'] = ''.join(temp).upper()
    
    from io import BytesIO
    f1 = BytesIO()
    img_obj.save(f1, format="PNG")
    img_data = f1.getvalue()
    
    return HttpResponse(img_data, content_type='image/png')


def login(request):
    err_msg = ''
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        v_code = request.POST.get('v_code', '').upper()
        
        if v_code == request.session.get('v_code'):
            obj = auth.authenticate(request, username=username, password=password)
            if obj:
                auth.login(request, obj)
                # 认证成功 初始化权限信息
                ret = init_permission(request, obj)
                if ret:
                    return ret
                return redirect(reverse('my_customer'))
            err_msg = '用户名或密码错误'
        else:
            err_msg = '验证码错误'
    
    return render(request, 'login.html', {'err_msg': err_msg})


# 注册
def reg(request):
    form_obj = RegForm()
    if request.method == 'POST':
        form_obj = RegForm(request.POST)
        if form_obj.is_valid():
            # 创建新用户
            # 方法一
            # form_obj.cleaned_data.pop('re_password')
            # models.UserProfile.objects.create_user(**form_obj.cleaned_data)
            
            # 方法二
            obj = form_obj.save()
            obj.set_password(obj.password)
            obj.save()
            
            return redirect('/login/')
    return render(request, 'reg.html', {'form_obj': form_obj})


# 展示客户列表
def customer_list(request):
    print(request.POST)
    
    if request.path_info == reverse('customer'):
        all_customer = models.Customer.objects.filter(consultant__isnull=True)
    else:
        all_customer = models.Customer.objects.filter(consultant=request.user)
    
    page = Pagination(request, all_customer.count())
    
    return render(request, 'crm/consultant/customer_list.html',
                  {"all_customer": all_customer[page.start:page.end], 'pagination': page.show_li})


# 展示客户列表CBV
class CustomerList(View):
    
    def get(self, request):
        
        q = self.get_search_contion(['qq', 'name', 'last_consult_date'])
        
        if request.path_info == reverse('customer'):
            # Q()
            all_customer = models.Customer.objects.filter(q, consultant__isnull=True)
        else:
            all_customer = models.Customer.objects.filter(q, consultant=request.user)
        
        # query_params = copy.deepcopy(request.GET)  # <QueryDict: {'query': ['alex']}>
        query_params = request.GET.copy()  # <QueryDict: {'query': ['alex']}>
        # query=alex
        # print(request.GET.urlencode())
        
        # query_params['page'] = 1  # <QueryDict: {'query': ['alex'],'page': ['1']}>
        # print(request.GET.urlencode())  # query=alex&page=1
        
        page = Pagination(request, all_customer.count(), query_params, )
        
        # 生成添加按钮
        add_btn, query_params = self.get_add_btn()
        
        return render(request, 'crm/consultant/customer_list.html',
                      {"all_customer": all_customer[page.start:page.end], 'pagination': page.show_li,
                       'add_btn': add_btn, 'query_params': query_params})
    
    def post(self, request):
        # 处理post提交的action的动作
        print(request.POST)
        # action = multi_apply   ; id = [1,4,5]
        
        action = request.POST.get('action')
        
        if not hasattr(self, action):
            return HttpResponse('非法操作')
        
        ret = getattr(self, action)()
        
        if ret:
            return ret
        
        return self.get(request)
    
    def multi_apply(self):
        # 公户变私户
        ids = self.request.POST.getlist('id')
        # 方法一
        # models.Customer.objects.filter(id__in=ids).update(consultant=self.request.user)
        
        # 方法二
        # self.request.user.customers.add(*models.Customer.objects.filter(id__in=ids))
        apply_num = len(ids)
        
        # 用户总数不能超过设置值
        if self.request.user.customers.count() + apply_num > settings.CUSTOMER_MAX_NUM:
            return HttpResponse('做人不要太贪心，给别人的机会')
        
        with transaction.atomic():
            # 事务：
            # select_for_update 加锁
            obj_list = models.Customer.objects.filter(id__in=ids, consultant__isnull=True).select_for_update()
            
            if apply_num == len(obj_list):
                # time.sleep(5)
                obj_list.update(consultant=self.request.user)
            else:
                return HttpResponse('你手速太慢了，已经被别人抢走了')
    
    def multi_pub(self):
        # 私户变公户
        
        ids = self.request.POST.getlist('id')
        # 方法一
        # models.Customer.objects.filter(id__in=ids).update(consultant=None)
        
        # 方法二
        self.request.user.customers.remove(*models.Customer.objects.filter(id__in=ids))
    
    def get_search_contion(self, fields_list):
        
        query = self.request.GET.get('query', '')
        
        q = Q()
        q.connector = 'OR'
        for i in fields_list:
            q.children.append(Q(('{}__contains'.format(i), query)))
        
        return q
        
        # Q( Q(qq__contains=query) |  Q(name__contains=query) )
    
    def get_add_btn(self):
        # 获取添加按钮
        
        url = self.request.get_full_path()
        
        qd = QueryDict()
        qd._mutable = True
        qd['next'] = url
        # next=%2Fcrm%2Fcustomer_list%2F%3Fquery%3Dalex%26page%3D2
        query_params = qd.urlencode()
        
        # add_btn = '<a href="{}?next={}" class="btn btn-primary btn-sm">添加</a>'.format(reverse('add_customer'), url)
        add_btn = '<a href="{}?{}" class="btn btn-primary btn-sm">添加</a>'.format(reverse('add_customer'), query_params)
        
        return mark_safe(add_btn), query_params


# 增加客户
def add_customer(request):
    # 实例化一个空的form对象
    form_obj = CustomerForm()
    if request.method == 'POST':
        # 实例化一个带提交数据的form对象
        form_obj = CustomerForm(request.POST)
        # 对提交数据进行校验
        if form_obj.is_valid():
            # 创建对象
            form_obj.save()
            return redirect(reverse('customer'))
    
    return render(request, 'crm/consultant/add_customer.html', {"form_obj": form_obj})


# 编辑客户
def edit_customer(request, edit_id):
    # 根据ID查出所需要编辑的客户对象
    obj = models.Customer.objects.filter(id=edit_id).first()
    form_obj = CustomerForm(instance=obj)
    if request.method == 'POST':
        # 将提交的数据和要修改的实例交给form对象
        form_obj = CustomerForm(request.POST, instance=obj)
        if form_obj.is_valid():
            form_obj.save()
            return redirect(reverse('customer'))
    
    return render(request, 'crm/consultant/edit_customer.html', {"form_obj": form_obj})


# 新增和编辑客户
def customer(request, edit_id=None):
    obj = models.Customer.objects.filter(id=edit_id).first()
    form_obj = CustomerForm(instance=obj)
    if request.method == 'POST':
        form_obj = CustomerForm(request.POST, instance=obj)
        if form_obj.is_valid():
            # 创建一个新的数据或修改原始数据
            form_obj.save()
            
            # 获取到next
            next = request.GET.get('next')
            if next:
                return redirect(next)
            return redirect(reverse('customer'))
    
    return render(request, 'crm/consultant/customer.html', {"form_obj": form_obj, "edit_id": edit_id})


# 展示跟进记录
class ConsultRecord(View):
    
    def get(self, request, customer_id):
        
        if customer_id == '0':
            all_consult_record = models.ConsultRecord.objects.filter(delete_status=False, consultant=request.user)
        else:
            all_consult_record = models.ConsultRecord.objects.filter(customer_id=customer_id, delete_status=False)
        return render(request, 'crm/consultant/consult_record_list.html',
                      {
                          'all_consult_record': all_consult_record
                      })


# 添加跟进记录
def add_consult_record(request):
    obj = models.ConsultRecord(consultant=request.user)
    
    form_obj = ConsultRecordForm(instance=obj)
    if request.method == 'POST':
        form_obj = ConsultRecordForm(request.POST)
        if form_obj.is_valid():
            form_obj.save()
            return redirect(reverse('consult_record'))
    
    return render(request, 'crm/consultant/add_consult_record.html', {'form_obj': form_obj})


# 编辑跟进记录
def edit_consult_record(request, edit_id):
    obj = models.ConsultRecord.objects.filter(id=edit_id).first()
    form_obj = ConsultRecordForm(instance=obj)
    if request.method == 'POST':
        form_obj = ConsultRecordForm(request.POST, instance=obj)
        if form_obj.is_valid():
            form_obj.save()
            return redirect(reverse('consult_record'))
    
    return render(request, 'crm/consultant/edit_consult_record.html', {'form_obj': form_obj})


# 新增和编辑跟进记录
def consult_record(request, edit_id=None):
    obj = models.ConsultRecord.objects.filter(id=edit_id).first() or models.ConsultRecord(consultant=request.user)
    form_obj = ConsultRecordForm(instance=obj)
    if request.method == 'POST':
        form_obj = ConsultRecordForm(request.POST, instance=obj)
        if form_obj.is_valid():
            form_obj.save()
            return redirect(reverse('consult_record', args=(0,)))
    
    return render(request, 'crm/consultant/edit_consult_record.html', {'form_obj': form_obj})


# 展示报名记录
class EnrollmentList(View):
    def get(self, request, customer_id):
        
        if customer_id == '0':
            all_record = models.Enrollment.objects.filter(delete_status=False, customer__consultant=request.user)
        else:
            all_record = models.Enrollment.objects.filter(customer_id=customer_id, delete_status=False)
        
        # 获取搜索条件
        query_params = self.get_query_params()
        
        return render(request, 'crm/consultant/enrollment_list.html',
                      {
                          'all_record': all_record,
                          'query_params': query_params
                      })
    
    def get_query_params(self):
        # 获取添加按钮
        
        url = self.request.get_full_path()
        
        qd = QueryDict()
        qd._mutable = True
        qd['next'] = url
        query_params = qd.urlencode()
        
        return query_params


# 添加报名记录
def enrollment(request, customer_id=None, edit_id=None):
    obj = models.Enrollment.objects.filter(id=edit_id).first() or models.Enrollment(customer_id=customer_id)
    form_obj = EnrollmentForm(instance=obj)
    if request.method == 'POST':
        form_obj = EnrollmentForm(request.POST, instance=obj)
        if form_obj.is_valid():
            enrollment_obj = form_obj.save()
            # 修改客户的状态
            
            enrollment_obj.customer.status = 'signed'
            enrollment_obj.customer.save()
            
            next = request.GET.get('next')
            if next:
                return redirect(next)
            else:
                return redirect(reverse('my_customer'))
    
    return render(request, 'crm/consultant/enrollment.html', {"form_obj": form_obj})


# 测试分页

# 测试数据

users = [{'name': 'alex{}'.format(i), 'pwd': 'alexdsb{}'.format(i)} for i in range(1, 302)]


# def user_list(request):
#     # 当前页码
#     try:
#         current_page = int(request.GET.get('page', 1))
#         if current_page <= 0:
#             current_page = 1
#     except Exception as e:
#         current_page = 1
#     # 最多显示的页码数
#     max_show = 11
#     half_show = max_show // 2
#
#     # 每页显示的数据条数
#     per_num = 10
#     # 总数据量
#     all_count = len(users)
#
#     # 总页码数
#     total_num, more = divmod(all_count, per_num)
#     if more:
#         total_num += 1
#
#     # 总页码数小于最大显示数：显示总页码数
#     if total_num <= max_show:
#         page_start = 1
#         page_end = total_num
#     else:
#         # 总页码数大于最大显示数：最多显示11个
#         if current_page <= half_show:
#             page_start = 1
#             page_end = max_show
#         elif current_page + half_show >= total_num:
#             page_end = total_num
#             page_start = total_num - max_show + 1
#         else:
#             page_start = current_page - half_show
#             page_end = current_page + half_show
#     # 存放li标签的列表
#     html_list = []
#
#     first_li = '<li><a href="/user_list/?page=1">首页</a></li>'
#     html_list.append(first_li)
#
#     if current_page == 1:
#         prev_li = '<li class="disabled"><a><<</a></li>'
#     else:
#         prev_li = '<li><a href="/user_list/?page={0}"><<</a></li>'.format(current_page - 1)
#     html_list.append(prev_li)
#
#     for num in range(page_start, page_end + 1):
#         if current_page == num:
#             li_html = '<li class="active"><a href="/user_list/?page={0}">{0}</a></li>'.format(num)
#         else:
#             li_html = '<li><a href="/user_list/?page={0}">{0}</a></li>'.format(num)
#         html_list.append(li_html)
#
#     if current_page == total_num:
#         next_li = '<li class="disabled"><a>>></a></li>'
#     else:
#         next_li = '<li><a href="/user_list/?page={0}">>></a></li>'.format(current_page + 1)
#
#     html_list.append(next_li)
#
#     last_li = '<li><a href="/user_list/?page={}">尾页</a></li>'.format(total_num)
#     html_list.append(last_li)
#
#     html_str = mark_safe(''.join(html_list))
#
#     """
#     1   0  10
#     2  10  20
#     """
#     # 切片的起始值
#     start = (current_page - 1) * per_num
#     # 切片的终止值
#     end = current_page * per_num
#
#     return render(request, 'user_list.html',
#                   {
#                       "data": users[start:end],
#                       # 'total_num': range(page_start, page_end + 1)
#                       'html_str': html_str
#                   })


def user_list(request):
    page = Pagination(request, len(users))
    
    return render(request, 'user_list.html',
                  {
                      "data": users[page.start:page.end],
                      # 'total_num': range(page_start, page_end + 1)
                      'html_str': page.show_li
                  })
