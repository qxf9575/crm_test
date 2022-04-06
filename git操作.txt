git checkout -b newbranch        # 创建newbranch分支
git push origin newbranch:newbranch #将本地的newbranch(:前面)分支推送到远程命名为newbranch(:后面)分支
git push origin --delete newbranch # 删除远程newbranch分支
git branch -d newbranch            # 删除本地newbranch分支（不能删除当前分支，需要先切换到其他分支）

git chechout main                # 切换到main分支
git merge new                    # 合并new分支到main分支
git push                         # 推送远程
git push origin --delete new     # 删除远程new分支

git tag 20220406                 # 创建20220406标签
git push origin --tags           # 推送标签到远程
git push origin -delete 20220406 # 删除标签
git push origin --tags           #推送标签到远程