from django.shortcuts import render, redirect, reverse, HttpResponse
from django.contrib import auth
from crm.forms import *
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
from django.views import View


# 班级列表展示
class ClassList(View):
    
    def get(self, request):
        # 模糊搜索
        q = self.get_search_contion(['course', 'semester'])
        
        all_class = models.ClassList.objects.filter(q)
        
        # 获取路径
        query_params = self.get_query_params()
        
        # 分页的应用
        page = Pagination(request, len(all_class), request.GET.copy())
        
        return render(request, 'crm/teacher/class_list.html',
                      {"all_class": all_class[page.start:page.end], 'pagination': page.show_li,
                       'query_params': query_params})
    
    def get_search_contion(self, fields_list):
        query = self.request.GET.get('query', '')
        
        q = Q()
        q.connector = 'OR'
        for i in fields_list:
            q.children.append(Q(('{}__contains'.format(i), query)))
        
        return q
    
    def get_query_params(self):
        url = self.request.get_full_path()
        
        qd = QueryDict()
        qd._mutable = True
        qd['next'] = url
        query_params = qd.urlencode()
        
        return query_params


# 添加、编辑班级
def classes(request, edit_id=None):
    obj = models.ClassList.objects.filter(id=edit_id).first()
    form_obj = ClassForm(instance=obj)
    title = '编辑班级' if obj else '新增班级'
    if request.method == 'POST':
        form_obj = ClassForm(request.POST, instance=obj)
        if form_obj.is_valid():
            form_obj.save()
            next = request.GET.get('next')
            if next:
                return redirect(next)
            return redirect(reverse('class_list'))
    
    return render(request, 'crm/form.html', {'title': title, 'form_obj': form_obj})


class CourseList(View):
    
    def get(self, request, class_id):
        # 模糊搜索
        q = self.get_search_contion([])
        
        all_course = models.CourseRecord.objects.filter(q, re_class_id=class_id)
        
        # 获取路径
        query_params = self.get_query_params()
        
        # 分页的应用
        page = Pagination(request, len(all_course), request.GET.copy())
        
        return render(request, 'crm/teacher/course_list.html',
                      {"all_course": all_course[page.start:page.end], 'pagination': page.show_li,
                       'query_params': query_params,
                       'class_id': class_id
                       })
    
    def post(self, request, class_id):
        
        action = request.POST.get('action')
        
        if not hasattr(self, action):
            return HttpResponse('非法操作')
        
        ret = getattr(self, action)()
        
        if ret:
            return ret
        
        return self.get(request, class_id)
    
    def get_search_contion(self, fields_list):
        query = self.request.GET.get('query', '')
        
        q = Q()
        q.connector = 'OR'
        for i in fields_list:
            q.children.append(Q(('{}__contains'.format(i), query)))
        
        return q
    
    def get_query_params(self):
        url = self.request.get_full_path()
        
        qd = QueryDict()
        qd._mutable = True
        qd['next'] = url
        query_params = qd.urlencode()
        
        return query_params
    
    def multi_init(self):
        # 根据当前提交的课程记录Id批量初识化学生的学习记录
        
        course_ids = self.request.POST.getlist('id')
        
        course_obj_list = models.CourseRecord.objects.filter(id__in=course_ids)
        
        for course_obj in course_obj_list:
            # 查询当前课程记录代表的班级的学生
            all_students = course_obj.re_class.customer_set.filter(status='studying')
            
            student_list = []
            
            for student in all_students:
                # models.StudyRecord.objects.create(course_record=course_obj, student=student)
                
                # obj = models.StudyRecord(course_record=course_obj, student=student)
                # obj.save()
                
                student_list.append(models.StudyRecord(course_record=course_obj, student=student))
            
            models.StudyRecord.objects.bulk_create(student_list)


def course(request, class_id=None, edit_id=None):
    obj = models.CourseRecord.objects.filter(id=edit_id).first() or models.CourseRecord(re_class_id=class_id,
                                                                                        teacher=request.user)
    form_obj = CourseForm(instance=obj)
    title = '编辑课程' if edit_id else '新增课程'
    if request.method == 'POST':
        form_obj = CourseForm(request.POST, instance=obj)
        if form_obj.is_valid():
            form_obj.save()
            next = request.GET.get('next')
            if next:
                return redirect(next)
            return redirect(reverse('course_list', args=(class_id,)))
    
    return render(request, 'crm/form.html', {'title': title, 'form_obj': form_obj, })


# 展示学习记录
from django.forms import modelformset_factory


def study_record(request, course_id):
    FormSet = modelformset_factory(models.StudyRecord, StudyRecordForm, extra=0)
    queryset = models.StudyRecord.objects.filter(course_record_id=course_id)
    form_set = FormSet(queryset=queryset)
    if request.method == 'POST':
        form_set = FormSet(request.POST)
        if form_set.is_valid():
            form_set.save()
    
    return render(request, 'crm/teacher/study_record_list.html', {"form_set": form_set})
