# Analysis
import numpy as np

import matplotlib as mpl
mpl.use('pdf')
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc    

mpColors=["blue","green","red","cyan","magenta","yellow","black","white"]

def MultiClassificationAnalysis(MyModel,Test_X=[],Test_Y=[],BatchSize=1024,PDFFileName=False,
                                IndexMap=False,MakePlot=True,result=False):

    if type(result)==bool:
        result = MyModel.Model.predict(Test_X, batch_size=BatchSize)

    # Unfortunately, we can use the generator, because we need Test_Y
    # result = MyModel.Model.predict_generator(validation_generator, batch_size=BatchSize)
    
    NClasses=Test_Y.shape[1]
    MetaData={}
    
    for ClassIndex in xrange(0,NClasses):
        fpr, tpr, _ = roc_curve(Test_Y[:,ClassIndex], 
                                result[:,ClassIndex])
        roc_auc = auc(fpr, tpr)    
    
        lw=2

        if IndexMap:
            ClassName=IndexMap[ClassIndex]
        else:
            ClassName="Class "+str(ClassIndex)

        MetaData[ClassName+"_AUC"]=roc_auc

        if MakePlot:
            plt.plot(fpr,tpr,color=mpColors[ClassIndex],
                     lw=lw, label=ClassName+ ' (area = %0.2f)' % roc_auc)

            plt.plot([0, 1], [0, 1], color='navy', lw=lw, linestyle='--')
            plt.xlim([0.0, 1.0])
            plt.ylim([0.0, 1.05])

            plt.xlabel('False Positive Rate')
            plt.ylabel('True Positive Rate')

            plt.legend(loc="lower right")
        
    if MakePlot and PDFFileName:
        try:
            plt.savefig(MyModel.OutDir+"/"+PDFFileName+".pdf")
        except:
            print "Warning: Unable to write out:",MyModel.OutDir+"/"+PDFFileName+".pdf"

    return result,MetaData


