# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'fragmerge_gui.ui'
##
## Created by: Qt User Interface Compiler version 6.10.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QPushButton,
    QRadioButton, QScrollArea, QSizePolicy, QSpacerItem,
    QSpinBox, QTabWidget, QVBoxLayout, QWidget)

class Ui_FragMergeApp(object):
    def setupUi(self, FragMergeApp):
        if not FragMergeApp.objectName():
            FragMergeApp.setObjectName(u"FragMergeApp")
        FragMergeApp.resize(1200, 760)
        self.centralwidget = QWidget(FragMergeApp)
        self.centralwidget.setObjectName(u"centralwidget")
        self.rootLayout = QHBoxLayout(self.centralwidget)
        self.rootLayout.setObjectName(u"rootLayout")
        self.rootLayout.setContentsMargins(8, 8, 8, 8)
        self.leftTabs = QTabWidget(self.centralwidget)
        self.leftTabs.setObjectName(u"leftTabs")
        self.tabMerge = QWidget()
        self.tabMerge.setObjectName(u"tabMerge")
        self.mergeLayout = QVBoxLayout(self.tabMerge)
        self.mergeLayout.setObjectName(u"mergeLayout")
        self.mergeLayout.setContentsMargins(8, 8, 8, 8)
        self.formatGroup = QGroupBox(self.tabMerge)
        self.formatGroup.setObjectName(u"formatGroup")
        self.formatLayout = QHBoxLayout(self.formatGroup)
        self.formatLayout.setObjectName(u"formatLayout")
        self.radioChara = QRadioButton(self.formatGroup)
        self.radioChara.setObjectName(u"radioChara")
        self.radioChara.setChecked(True)

        self.formatLayout.addWidget(self.radioChara)

        self.radioBg = QRadioButton(self.formatGroup)
        self.radioBg.setObjectName(u"radioBg")

        self.formatLayout.addWidget(self.radioBg)

        self.radio5pb = QRadioButton(self.formatGroup)
        self.radio5pb.setObjectName(u"radio5pb")

        self.formatLayout.addWidget(self.radio5pb)

        self.radioSg = QRadioButton(self.formatGroup)
        self.radioSg.setObjectName(u"radioSg")

        self.formatLayout.addWidget(self.radioSg)

        self.formatSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.formatLayout.addItem(self.formatSpacer)


        self.mergeLayout.addWidget(self.formatGroup)

        self.filesGroup = QGroupBox(self.tabMerge)
        self.filesGroup.setObjectName(u"filesGroup")
        self.filesLayout = QVBoxLayout(self.filesGroup)
        self.filesLayout.setObjectName(u"filesLayout")
        self.btnSrc1 = QPushButton(self.filesGroup)
        self.btnSrc1.setObjectName(u"btnSrc1")

        self.filesLayout.addWidget(self.btnSrc1)

        self.src1Label = QLabel(self.filesGroup)
        self.src1Label.setObjectName(u"src1Label")
        self.src1Label.setWordWrap(True)

        self.filesLayout.addWidget(self.src1Label)

        self.btnSrc2 = QPushButton(self.filesGroup)
        self.btnSrc2.setObjectName(u"btnSrc2")
        self.btnSrc2.setVisible(False)

        self.filesLayout.addWidget(self.btnSrc2)

        self.src2Label = QLabel(self.filesGroup)
        self.src2Label.setObjectName(u"src2Label")
        self.src2Label.setVisible(False)
        self.src2Label.setWordWrap(True)

        self.filesLayout.addWidget(self.src2Label)

        self.btnDat = QPushButton(self.filesGroup)
        self.btnDat.setObjectName(u"btnDat")

        self.filesLayout.addWidget(self.btnDat)

        self.datLabel = QLabel(self.filesGroup)
        self.datLabel.setObjectName(u"datLabel")
        self.datLabel.setWordWrap(True)

        self.filesLayout.addWidget(self.datLabel)

        self.openRow = QHBoxLayout()
        self.openRow.setObjectName(u"openRow")
        self.btnOpenAuto = QPushButton(self.filesGroup)
        self.btnOpenAuto.setObjectName(u"btnOpenAuto")

        self.openRow.addWidget(self.btnOpenAuto)

        self.btnOpenFolder = QPushButton(self.filesGroup)
        self.btnOpenFolder.setObjectName(u"btnOpenFolder")

        self.openRow.addWidget(self.btnOpenFolder)


        self.filesLayout.addLayout(self.openRow)

        self.scaleRow = QHBoxLayout()
        self.scaleRow.setObjectName(u"scaleRow")
        self.scaleLabel = QLabel(self.filesGroup)
        self.scaleLabel.setObjectName(u"scaleLabel")
        self.scaleLabel.setVisible(False)

        self.scaleRow.addWidget(self.scaleLabel)

        self.scaleEntry = QLineEdit(self.filesGroup)
        self.scaleEntry.setObjectName(u"scaleEntry")
        self.scaleEntry.setVisible(False)

        self.scaleRow.addWidget(self.scaleEntry)

        self.scaleHint = QLabel(self.filesGroup)
        self.scaleHint.setObjectName(u"scaleHint")
        self.scaleHint.setVisible(False)

        self.scaleRow.addWidget(self.scaleHint)


        self.filesLayout.addLayout(self.scaleRow)


        self.mergeLayout.addWidget(self.filesGroup)

        self.descriptorsGroup = QGroupBox(self.tabMerge)
        self.descriptorsGroup.setObjectName(u"descriptorsGroup")
        self.descriptorsLayout = QVBoxLayout(self.descriptorsGroup)
        self.descriptorsLayout.setObjectName(u"descriptorsLayout")
        self.descriptorList = QListWidget(self.descriptorsGroup)
        self.descriptorList.setObjectName(u"descriptorList")

        self.descriptorsLayout.addWidget(self.descriptorList)

        self.listInfoLabel = QLabel(self.descriptorsGroup)
        self.listInfoLabel.setObjectName(u"listInfoLabel")
        self.listInfoLabel.setWordWrap(True)

        self.descriptorsLayout.addWidget(self.listInfoLabel)


        self.mergeLayout.addWidget(self.descriptorsGroup)

        self.actionButtonsLayout = QHBoxLayout()
        self.actionButtonsLayout.setObjectName(u"actionButtonsLayout")
        self.btnPreview = QPushButton(self.tabMerge)
        self.btnPreview.setObjectName(u"btnPreview")

        self.actionButtonsLayout.addWidget(self.btnPreview)

        self.btnSave = QPushButton(self.tabMerge)
        self.btnSave.setObjectName(u"btnSave")

        self.actionButtonsLayout.addWidget(self.btnSave)


        self.mergeLayout.addLayout(self.actionButtonsLayout)

        self.fragmentsGroup = QGroupBox(self.tabMerge)
        self.fragmentsGroup.setObjectName(u"fragmentsGroup")
        self.fragmentsLayout = QVBoxLayout(self.fragmentsGroup)
        self.fragmentsLayout.setObjectName(u"fragmentsLayout")
        self.fragScrollArea = QScrollArea(self.fragmentsGroup)
        self.fragScrollArea.setObjectName(u"fragScrollArea")
        self.fragScrollArea.setWidgetResizable(True)
        self.fragInnerWidget = QWidget()
        self.fragInnerWidget.setObjectName(u"fragInnerWidget")
        self.fragInnerWidget.setGeometry(QRect(0, 0, 547, 83))
        self.fragListLayout = QVBoxLayout(self.fragInnerWidget)
        self.fragListLayout.setObjectName(u"fragListLayout")
        self.fragScrollArea.setWidget(self.fragInnerWidget)

        self.fragmentsLayout.addWidget(self.fragScrollArea)

        self.fragBtnRow = QHBoxLayout()
        self.fragBtnRow.setObjectName(u"fragBtnRow")
        self.btnFragAll = QPushButton(self.fragmentsGroup)
        self.btnFragAll.setObjectName(u"btnFragAll")

        self.fragBtnRow.addWidget(self.btnFragAll)

        self.btnFragNone = QPushButton(self.fragmentsGroup)
        self.btnFragNone.setObjectName(u"btnFragNone")

        self.fragBtnRow.addWidget(self.btnFragNone)


        self.fragmentsLayout.addLayout(self.fragBtnRow)


        self.mergeLayout.addWidget(self.fragmentsGroup)

        self.statusLabel = QLabel(self.tabMerge)
        self.statusLabel.setObjectName(u"statusLabel")
        self.statusLabel.setFrameShape(QFrame.Shape.Panel)
        self.statusLabel.setFrameShadow(QFrame.Shadow.Sunken)

        self.mergeLayout.addWidget(self.statusLabel)

        self.leftTabs.addTab(self.tabMerge, "")
        self.tabDebug = QWidget()
        self.tabDebug.setObjectName(u"tabDebug")
        self.debugLayout = QVBoxLayout(self.tabDebug)
        self.debugLayout.setObjectName(u"debugLayout")
        self.debugLayout.setContentsMargins(8, 8, 8, 8)
        self.dumpSingleGroup = QGroupBox(self.tabDebug)
        self.dumpSingleGroup.setObjectName(u"dumpSingleGroup")
        self.dumpSingleLayout = QVBoxLayout(self.dumpSingleGroup)
        self.dumpSingleLayout.setObjectName(u"dumpSingleLayout")
        self.btnDumpSlices = QPushButton(self.dumpSingleGroup)
        self.btnDumpSlices.setObjectName(u"btnDumpSlices")

        self.dumpSingleLayout.addWidget(self.btnDumpSlices)

        self.btnDumpImages = QPushButton(self.dumpSingleGroup)
        self.btnDumpImages.setObjectName(u"btnDumpImages")

        self.dumpSingleLayout.addWidget(self.btnDumpImages)

        self.dumpSingleInfo = QLabel(self.dumpSingleGroup)
        self.dumpSingleInfo.setObjectName(u"dumpSingleInfo")
        self.dumpSingleInfo.setWordWrap(True)

        self.dumpSingleLayout.addWidget(self.dumpSingleInfo)


        self.debugLayout.addWidget(self.dumpSingleGroup)

        self.dumpAllGroup = QGroupBox(self.tabDebug)
        self.dumpAllGroup.setObjectName(u"dumpAllGroup")
        self.dumpAllLayout = QVBoxLayout(self.dumpAllGroup)
        self.dumpAllLayout.setObjectName(u"dumpAllLayout")
        self.dumpAllFmtRow = QHBoxLayout()
        self.dumpAllFmtRow.setObjectName(u"dumpAllFmtRow")
        self.dumpAllFmtLabel = QLabel(self.dumpAllGroup)
        self.dumpAllFmtLabel.setObjectName(u"dumpAllFmtLabel")

        self.dumpAllFmtRow.addWidget(self.dumpAllFmtLabel)

        self.dumpAllFmt = QComboBox(self.dumpAllGroup)
        self.dumpAllFmt.addItem("")
        self.dumpAllFmt.addItem("")
        self.dumpAllFmt.addItem("")
        self.dumpAllFmt.addItem("")
        self.dumpAllFmt.setObjectName(u"dumpAllFmt")

        self.dumpAllFmtRow.addWidget(self.dumpAllFmt)

        self.dumpAllFmtSpacer = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.dumpAllFmtRow.addItem(self.dumpAllFmtSpacer)

        self.dumpAllWorkersLabel = QLabel(self.dumpAllGroup)
        self.dumpAllWorkersLabel.setObjectName(u"dumpAllWorkersLabel")

        self.dumpAllFmtRow.addWidget(self.dumpAllWorkersLabel)

        self.dumpAllWorkers = QSpinBox(self.dumpAllGroup)
        self.dumpAllWorkers.setObjectName(u"dumpAllWorkers")
        self.dumpAllWorkers.setMinimum(1)
        self.dumpAllWorkers.setMaximum(64)
        self.dumpAllWorkers.setValue(1)

        self.dumpAllFmtRow.addWidget(self.dumpAllWorkers)


        self.dumpAllLayout.addLayout(self.dumpAllFmtRow)

        self.dumpAllDirRow = QHBoxLayout()
        self.dumpAllDirRow.setObjectName(u"dumpAllDirRow")
        self.dumpAllDir = QLineEdit(self.dumpAllGroup)
        self.dumpAllDir.setObjectName(u"dumpAllDir")

        self.dumpAllDirRow.addWidget(self.dumpAllDir)

        self.btnDumpAllDir = QPushButton(self.dumpAllGroup)
        self.btnDumpAllDir.setObjectName(u"btnDumpAllDir")

        self.dumpAllDirRow.addWidget(self.btnDumpAllDir)


        self.dumpAllLayout.addLayout(self.dumpAllDirRow)

        self.dumpAllOutRow = QHBoxLayout()
        self.dumpAllOutRow.setObjectName(u"dumpAllOutRow")
        self.dumpAllOut = QLineEdit(self.dumpAllGroup)
        self.dumpAllOut.setObjectName(u"dumpAllOut")

        self.dumpAllOutRow.addWidget(self.dumpAllOut)

        self.btnDumpAllOut = QPushButton(self.dumpAllGroup)
        self.btnDumpAllOut.setObjectName(u"btnDumpAllOut")

        self.dumpAllOutRow.addWidget(self.btnDumpAllOut)


        self.dumpAllLayout.addLayout(self.dumpAllOutRow)

        self.btnDumpAllRun = QPushButton(self.dumpAllGroup)
        self.btnDumpAllRun.setObjectName(u"btnDumpAllRun")

        self.dumpAllLayout.addWidget(self.btnDumpAllRun)

        self.dumpAllInfo = QLabel(self.dumpAllGroup)
        self.dumpAllInfo.setObjectName(u"dumpAllInfo")
        self.dumpAllInfo.setWordWrap(True)

        self.dumpAllLayout.addWidget(self.dumpAllInfo)


        self.debugLayout.addWidget(self.dumpAllGroup)

        self.reconGroup = QGroupBox(self.tabDebug)
        self.reconGroup.setObjectName(u"reconGroup")
        self.reconLayout = QVBoxLayout(self.reconGroup)
        self.reconLayout.setObjectName(u"reconLayout")
        self.reconFmtRow = QHBoxLayout()
        self.reconFmtRow.setObjectName(u"reconFmtRow")
        self.reconFmtLabel = QLabel(self.reconGroup)
        self.reconFmtLabel.setObjectName(u"reconFmtLabel")

        self.reconFmtRow.addWidget(self.reconFmtLabel)

        self.reconFmt = QComboBox(self.reconGroup)
        self.reconFmt.addItem("")
        self.reconFmt.addItem("")
        self.reconFmt.addItem("")
        self.reconFmt.addItem("")
        self.reconFmt.setObjectName(u"reconFmt")

        self.reconFmtRow.addWidget(self.reconFmt)

        self.reconFmtSpacer = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.reconFmtRow.addItem(self.reconFmtSpacer)

        self.reconWorkersLabel = QLabel(self.reconGroup)
        self.reconWorkersLabel.setObjectName(u"reconWorkersLabel")

        self.reconFmtRow.addWidget(self.reconWorkersLabel)

        self.reconWorkers = QSpinBox(self.reconGroup)
        self.reconWorkers.setObjectName(u"reconWorkers")
        self.reconWorkers.setMinimum(1)
        self.reconWorkers.setMaximum(64)
        self.reconWorkers.setValue(1)

        self.reconFmtRow.addWidget(self.reconWorkers)


        self.reconLayout.addLayout(self.reconFmtRow)

        self.reconDirRow = QHBoxLayout()
        self.reconDirRow.setObjectName(u"reconDirRow")
        self.reconDir = QLineEdit(self.reconGroup)
        self.reconDir.setObjectName(u"reconDir")

        self.reconDirRow.addWidget(self.reconDir)

        self.btnReconDir = QPushButton(self.reconGroup)
        self.btnReconDir.setObjectName(u"btnReconDir")

        self.reconDirRow.addWidget(self.btnReconDir)


        self.reconLayout.addLayout(self.reconDirRow)

        self.reconOutRow = QHBoxLayout()
        self.reconOutRow.setObjectName(u"reconOutRow")
        self.reconOut = QLineEdit(self.reconGroup)
        self.reconOut.setObjectName(u"reconOut")

        self.reconOutRow.addWidget(self.reconOut)

        self.btnReconOut = QPushButton(self.reconGroup)
        self.btnReconOut.setObjectName(u"btnReconOut")

        self.reconOutRow.addWidget(self.btnReconOut)


        self.reconLayout.addLayout(self.reconOutRow)

        self.btnReconRun = QPushButton(self.reconGroup)
        self.btnReconRun.setObjectName(u"btnReconRun")

        self.reconLayout.addWidget(self.btnReconRun)

        self.reconInfo = QLabel(self.reconGroup)
        self.reconInfo.setObjectName(u"reconInfo")
        self.reconInfo.setWordWrap(True)

        self.reconLayout.addWidget(self.reconInfo)


        self.debugLayout.addWidget(self.reconGroup)

        self.debugSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.debugLayout.addItem(self.debugSpacer)

        self.leftTabs.addTab(self.tabDebug, "")

        self.rootLayout.addWidget(self.leftTabs)

        self.rightLayout = QVBoxLayout()
        self.rightLayout.setObjectName(u"rightLayout")
        self.previewLabel = QLabel(self.centralwidget)
        self.previewLabel.setObjectName(u"previewLabel")

        self.rightLayout.addWidget(self.previewLabel)

        self.zoomRow = QHBoxLayout()
        self.zoomRow.setObjectName(u"zoomRow")
        self.whiteBgCheck = QCheckBox(self.centralwidget)
        self.whiteBgCheck.setObjectName(u"whiteBgCheck")

        self.zoomRow.addWidget(self.whiteBgCheck)

        self.btnZoomOut = QPushButton(self.centralwidget)
        self.btnZoomOut.setObjectName(u"btnZoomOut")

        self.zoomRow.addWidget(self.btnZoomOut)

        self.btnZoomReset = QPushButton(self.centralwidget)
        self.btnZoomReset.setObjectName(u"btnZoomReset")

        self.zoomRow.addWidget(self.btnZoomReset)

        self.btnZoomIn = QPushButton(self.centralwidget)
        self.btnZoomIn.setObjectName(u"btnZoomIn")

        self.zoomRow.addWidget(self.btnZoomIn)

        self.zoomLabel = QLabel(self.centralwidget)
        self.zoomLabel.setObjectName(u"zoomLabel")

        self.zoomRow.addWidget(self.zoomLabel)

        self.zoomSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.zoomRow.addItem(self.zoomSpacer)


        self.rightLayout.addLayout(self.zoomRow)

        self.canvasScrollArea = QScrollArea(self.centralwidget)
        self.canvasScrollArea.setObjectName(u"canvasScrollArea")
        self.canvasScrollArea.setStyleSheet(u"background:#222")
        self.canvasScrollArea.setWidgetResizable(True)
        self.canvasScrollAreaWidgetContents = QWidget()
        self.canvasScrollAreaWidgetContents.setObjectName(u"canvasScrollAreaWidgetContents")
        self.canvasScrollAreaWidgetContents.setGeometry(QRect(0, 0, 583, 672))
        self.canvasLayout = QVBoxLayout(self.canvasScrollAreaWidgetContents)
        self.canvasLayout.setObjectName(u"canvasLayout")
        self.canvasLabel = QLabel(self.canvasScrollAreaWidgetContents)
        self.canvasLabel.setObjectName(u"canvasLabel")
        self.canvasLabel.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop)

        self.canvasLayout.addWidget(self.canvasLabel)

        self.canvasScrollArea.setWidget(self.canvasScrollAreaWidgetContents)

        self.rightLayout.addWidget(self.canvasScrollArea)


        self.rootLayout.addLayout(self.rightLayout)

        FragMergeApp.setCentralWidget(self.centralwidget)

        self.retranslateUi(FragMergeApp)

        self.leftTabs.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(FragMergeApp)
    # setupUi

    def retranslateUi(self, FragMergeApp):
        FragMergeApp.setWindowTitle(QCoreApplication.translate("FragMergeApp", u"FragMerge - slice reassembler", None))
        self.formatGroup.setTitle(QCoreApplication.translate("FragMergeApp", u"Format", None))
        self.radioChara.setText(QCoreApplication.translate("FragMergeApp", u"11eyes chara", None))
        self.radioBg.setText(QCoreApplication.translate("FragMergeApp", u"11eyes bg", None))
        self.radio5pb.setText(QCoreApplication.translate("FragMergeApp", u"5pb", None))
        self.radioSg.setText(QCoreApplication.translate("FragMergeApp", u"sg (PC)", None))
        self.filesGroup.setTitle(QCoreApplication.translate("FragMergeApp", u"Files", None))
        self.btnSrc1.setText(QCoreApplication.translate("FragMergeApp", u"Source image 1", None))
        self.src1Label.setText("")
        self.btnSrc2.setText(QCoreApplication.translate("FragMergeApp", u"Source image 2 (bg)", None))
        self.src2Label.setText("")
        self.btnDat.setText(QCoreApplication.translate("FragMergeApp", u"Descriptor .dat / .bin", None))
        self.datLabel.setText("")
        self.btnOpenAuto.setText(QCoreApplication.translate("FragMergeApp", u"Open (auto)", None))
        self.btnOpenFolder.setText(QCoreApplication.translate("FragMergeApp", u"Open folder", None))
        self.scaleLabel.setText(QCoreApplication.translate("FragMergeApp", u"5pb src scale:", None))
        self.scaleEntry.setText(QCoreApplication.translate("FragMergeApp", u"auto", None))
        self.scaleHint.setText(QCoreApplication.translate("FragMergeApp", u"(auto/256/512/1024/2048)", None))
        self.descriptorsGroup.setTitle(QCoreApplication.translate("FragMergeApp", u"Descriptors (from extraction sidecars)", None))
        self.listInfoLabel.setText(QCoreApplication.translate("FragMergeApp", u"Open a folder to list its descriptors.", None))
        self.btnPreview.setText(QCoreApplication.translate("FragMergeApp", u"Preview", None))
        self.btnSave.setText(QCoreApplication.translate("FragMergeApp", u"Save PNG/BMP", None))
        self.fragmentsGroup.setTitle(QCoreApplication.translate("FragMergeApp", u"Fragments (toggle to include)", None))
        self.btnFragAll.setText(QCoreApplication.translate("FragMergeApp", u"All", None))
        self.btnFragNone.setText(QCoreApplication.translate("FragMergeApp", u"None", None))
        self.statusLabel.setText(QCoreApplication.translate("FragMergeApp", u"Load files, then Preview (or use Open).", None))
        self.leftTabs.setTabText(self.leftTabs.indexOf(self.tabMerge), QCoreApplication.translate("FragMergeApp", u"Merge", None))
        self.dumpSingleGroup.setTitle(QCoreApplication.translate("FragMergeApp", u"Single descriptor", None))
        self.btnDumpSlices.setText(QCoreApplication.translate("FragMergeApp", u"Dump slices (text grid)", None))
        self.btnDumpImages.setText(QCoreApplication.translate("FragMergeApp", u"Dump slice images (PNGs)", None))
        self.dumpSingleInfo.setText(QCoreApplication.translate("FragMergeApp", u"Uses the currently loaded format, source image(s) and descriptor.", None))
        self.dumpAllGroup.setTitle(QCoreApplication.translate("FragMergeApp", u"Batch: dump all descriptors in a folder", None))
        self.dumpAllFmtLabel.setText(QCoreApplication.translate("FragMergeApp", u"Format:", None))
        self.dumpAllFmt.setItemText(0, QCoreApplication.translate("FragMergeApp", u"chara", None))
        self.dumpAllFmt.setItemText(1, QCoreApplication.translate("FragMergeApp", u"bg", None))
        self.dumpAllFmt.setItemText(2, QCoreApplication.translate("FragMergeApp", u"5pb", None))
        self.dumpAllFmt.setItemText(3, QCoreApplication.translate("FragMergeApp", u"sg", None))

        self.dumpAllWorkersLabel.setText(QCoreApplication.translate("FragMergeApp", u"Workers:", None))
        self.dumpAllDir.setText("")
        self.dumpAllDir.setPlaceholderText(QCoreApplication.translate("FragMergeApp", u"extraction folder (file_*.bin + file_*.png)", None))
        self.btnDumpAllDir.setText(QCoreApplication.translate("FragMergeApp", u"Browse\u2026", None))
        self.dumpAllOut.setText("")
        self.dumpAllOut.setPlaceholderText(QCoreApplication.translate("FragMergeApp", u"output folder for strips + manifests", None))
        self.btnDumpAllOut.setText(QCoreApplication.translate("FragMergeApp", u"Browse\u2026", None))
        self.btnDumpAllRun.setText(QCoreApplication.translate("FragMergeApp", u"Run batch dump", None))
        self.dumpAllInfo.setText(QCoreApplication.translate("FragMergeApp", u"Each descriptor becomes file_NNNN/file_NNNN_frag_MMM/ with strips + manifest.json.", None))
        self.reconGroup.setTitle(QCoreApplication.translate("FragMergeApp", u"Reconstruct fragments (per-fragment canvases)", None))
        self.reconFmtLabel.setText(QCoreApplication.translate("FragMergeApp", u"Format:", None))
        self.reconFmt.setItemText(0, QCoreApplication.translate("FragMergeApp", u"chara", None))
        self.reconFmt.setItemText(1, QCoreApplication.translate("FragMergeApp", u"bg", None))
        self.reconFmt.setItemText(2, QCoreApplication.translate("FragMergeApp", u"5pb", None))
        self.reconFmt.setItemText(3, QCoreApplication.translate("FragMergeApp", u"sg", None))

        self.reconWorkersLabel.setText(QCoreApplication.translate("FragMergeApp", u"Workers:", None))
        self.reconDir.setText("")
        self.reconDir.setPlaceholderText(QCoreApplication.translate("FragMergeApp", u"extraction folder (file_*.bin + file_*.png)", None))
        self.btnReconDir.setText(QCoreApplication.translate("FragMergeApp", u"Browse\u2026", None))
        self.reconOut.setText("")
        self.reconOut.setPlaceholderText(QCoreApplication.translate("FragMergeApp", u"output folder for per-fragment canvases", None))
        self.btnReconOut.setText(QCoreApplication.translate("FragMergeApp", u"Browse\u2026", None))
        self.btnReconRun.setText(QCoreApplication.translate("FragMergeApp", u"Run reconstruct", None))
        self.reconInfo.setText(QCoreApplication.translate("FragMergeApp", u"Each descriptor's fragment fi is rendered into its own canvas: file_NNNN/file_NNNN_frag_MMM/frag_MMM.png.", None))
        self.leftTabs.setTabText(self.leftTabs.indexOf(self.tabDebug), QCoreApplication.translate("FragMergeApp", u"Debug", None))
        self.previewLabel.setText(QCoreApplication.translate("FragMergeApp", u"Preview", None))
#if QT_CONFIG(tooltip)
        self.whiteBgCheck.setToolTip(QCoreApplication.translate("FragMergeApp", u"Composite the preview over opaque white instead of transparent.", None))
#endif // QT_CONFIG(tooltip)
        self.whiteBgCheck.setText(QCoreApplication.translate("FragMergeApp", u"White background", None))
        self.btnZoomOut.setText(QCoreApplication.translate("FragMergeApp", u"\u2212", None))
        self.btnZoomReset.setText(QCoreApplication.translate("FragMergeApp", u"100%", None))
        self.btnZoomIn.setText(QCoreApplication.translate("FragMergeApp", u"+", None))
        self.zoomLabel.setText(QCoreApplication.translate("FragMergeApp", u"fit", None))
    # retranslateUi

